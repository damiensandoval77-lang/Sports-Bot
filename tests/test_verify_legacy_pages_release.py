"""Byte-accurate source-mode Pages release checks; never touch remote service."""
import hashlib
import importlib.util
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("legacy_pages_checker",ROOT/"scripts/verify_legacy_pages_release.py")
checker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

class PagesVerificationTests(unittest.TestCase):
    def test_cli_creates_nested_receipt_directory_in_fresh_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/"new"/"nested"/"receipt.json"
            with patch.object(checker.sys,"argv",["verify",str(output)]), patch.object(
                    checker,"verify_with_retry",return_value={"status":"PASS"}):
                self.assertEqual(checker.main(),0)
            self.assertTrue(output.is_file())

    def test_phone_e2e_waits_for_publication_and_surfaces_failed_convergence(self):
        workflow=(ROOT/".github/workflows/live-site-e2e.yml").read_text()
        self.assertLess(workflow.index("python scripts/verify_legacy_pages_release.py"),
                        workflow.index("python scripts/e2e_live_site.py"))
        self.assertIn("steps.deployment.outputs.code != '0'",workflow)
        self.assertIn("steps.verify.outputs.code != '0'",workflow)
        self.assertIn("ref: main",workflow)

    def test_unchanged_manifest_and_all_served_assets_pass(self):
        assets={name:(name+" real code").encode() for name in
                ("feeds.js","live_direct.js","dames_take.js","provisional.js","short_history.js","index.html")}
        pins={name:checker.git_blob_sha(data) for name,data in assets.items()}
        manifest={"release_id":"dp-test-r1","asset_blob_sha1":pins}
        report=checker.evaluate(manifest,manifest,assets)
        self.assertEqual(report["status"],"PASS")
        self.assertTrue(all(c["pass"] for c in report["checks"]))

    def test_stale_bundle_cannot_fake_live_release(self):
        assets={name:(name+" latest").encode() for name in
                ("feeds.js","live_direct.js","dames_take.js","provisional.js","short_history.js","index.html")}
        manifest={"release_id":"dp-test-r2","asset_blob_sha1":
                  {name:checker.git_blob_sha(data) for name,data in assets.items()}}
        stale={**assets,"feeds.js":b"old code"}
        self.assertEqual(checker.evaluate(manifest,manifest,stale)["status"],"FAIL")

    def test_old_release_id_cannot_pass_even_with_matching_assets(self):
        assets={name:bytes(name,"utf8") for name in
                ("feeds.js","live_direct.js","dames_take.js","provisional.js","short_history.js","index.html")}
        manifest={"release_id":"dp-test-r3","asset_blob_sha1":
                  {name:checker.git_blob_sha(data) for name,data in assets.items()}}
        previous={**manifest,"release_id":"dp-test-r2"}
        self.assertEqual(checker.evaluate(manifest,previous,assets)["status"],"FAIL")

    def test_git_blob_hash_is_not_plain_sha1(self):
        data=b"real deployed asset"
        expected=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        self.assertEqual(checker.git_blob_sha(data),expected)
        self.assertNotEqual(checker.git_blob_sha(data),hashlib.sha1(data).hexdigest())

class RetryBudgetTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.assets = {name: name.encode() for name in
                       ('feeds.js', 'live_direct.js', 'dames_take.js',
                        'provisional.js', 'short_history.js', 'index.html')}
        self.manifest = {'release_id': 'test-exact', 'asset_blob_sha1':
                         {name: checker.git_blob_sha(data)
                          for name, data in self.assets.items()}}
        self.attempt = 0
        self.timeouts = []

    def sleep(self, seconds):
        self.now += seconds

    def run_checker(self, fetcher):
        return checker.verify_with_retry(self.manifest, fetcher=fetcher,
                                         clock=lambda: self.now, sleep=self.sleep)

    def fetch(self, name, timeout):
        import json
        self.timeouts.append(timeout)
        if name == 'release.json':
            self.attempt += 1
            return json.dumps(self.manifest).encode()
        return self.assets[name]

    def test_transient_404_then_stale_assets_eventually_pass(self):
        import urllib.error
        def fetch(name, timeout):
            data = self.fetch(name, timeout)
            if self.attempt < 3:
                raise urllib.error.HTTPError('https://example.invalid', 404, 'Not Found', {}, None)
            # Persist past the original three-attempt budget.
            if self.attempt < 8 and name == 'short_history.js':
                return b'superseded asset'
            return data
        report = self.run_checker(fetch)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['attempt'], 8)
        self.assertEqual(report['elapsed_seconds'], 84)
        self.assertTrue(all(check['pass'] for check in report['checks']))

    def test_persistent_stale_bytes_never_pass(self):
        def fetch(name, timeout):
            data = self.fetch(name, timeout)
            return b'stale' if name == 'index.html' else data
        report = self.run_checker(fetch)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['elapsed_seconds'], 360)
        self.assertEqual(report['attempt'], 30)
        self.assertFalse(next(c for c in report['checks'] if c['name'] == 'served_asset_index.html')['pass'])

    def test_persistent_404_never_pass(self):
        import urllib.error
        def fetch(name, timeout):
            raise urllib.error.HTTPError('https://example.invalid', 404, 'Not Found', {}, None)
        report = self.run_checker(fetch)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['elapsed_seconds'], 360)
        self.assertIn('HTTPError', report['error'])

    def test_slow_requests_share_budget_and_timeout_is_capped(self):
        def fetch(name, timeout):
            self.timeouts.append(timeout)
            self.now += timeout
            raise TimeoutError('slow remote')
        report = self.run_checker(fetch)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['elapsed_seconds'], 360)
        self.assertTrue(all(0 < t <= 25 for t in self.timeouts))
        self.assertEqual(self.timeouts[-1], 25)
        self.now = 0
        self.timeouts = []
        report = checker.verify_with_retry(self.manifest, fetcher=fetch,
            clock=lambda: self.now, sleep=self.sleep, budget=45)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['elapsed_seconds'], 45)
        self.assertEqual(self.timeouts, [25, 8])

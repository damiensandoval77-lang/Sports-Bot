"""Byte-accurate source-mode Pages release checks; never touch remote service."""
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("legacy_pages_checker",ROOT/"scripts/verify_legacy_pages_release.py")
checker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

class PagesVerificationTests(unittest.TestCase):
    def test_unchanged_manifest_and_all_served_assets_pass(self):
        assets={name:(name+" real code").encode() for name in
                ("feeds.js","live_direct.js","dames_take.js","provisional.js","index.html")}
        pins={name:checker.git_blob_sha(data) for name,data in assets.items()}
        manifest={"release_id":"dp-test-r1","asset_blob_sha1":pins}
        report=checker.evaluate(manifest,manifest,assets)
        self.assertEqual(report["status"],"PASS")
        self.assertTrue(all(c["pass"] for c in report["checks"]))

    def test_stale_bundle_cannot_fake_live_release(self):
        assets={name:(name+" latest").encode() for name in
                ("feeds.js","live_direct.js","dames_take.js","provisional.js","index.html")}
        manifest={"release_id":"dp-test-r2","asset_blob_sha1":
                  {name:checker.git_blob_sha(data) for name,data in assets.items()}}
        stale={**assets,"feeds.js":b"old code"}
        self.assertEqual(checker.evaluate(manifest,manifest,stale)["status"],"FAIL")

    def test_old_release_id_cannot_pass_even_with_matching_assets(self):
        assets={name:bytes(name,"utf8") for name in
                ("feeds.js","live_direct.js","dames_take.js","provisional.js","index.html")}
        manifest={"release_id":"dp-test-r3","asset_blob_sha1":
                  {name:checker.git_blob_sha(data) for name,data in assets.items()}}
        previous={**manifest,"release_id":"dp-test-r2"}
        self.assertEqual(checker.evaluate(manifest,previous,assets)["status"],"FAIL")

    def test_git_blob_hash_is_not_plain_sha1(self):
        data=b"real deployed asset"
        expected=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        self.assertEqual(checker.git_blob_sha(data),expected)
        self.assertNotEqual(checker.git_blob_sha(data),hashlib.sha1(data).hexdigest())

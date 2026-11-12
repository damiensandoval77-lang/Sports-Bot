import json
import unittest

from scripts.verify_public_dames_release import FILES,inspect,evaluate,git_blob_digest,validate_manifest


class PublicReleaseGateTest(unittest.TestCase):
    def files(self):
        html=b'<meta name="dames-release" content="dp-hit-est-20261111-r1"> Hit est. HIT EST.'
        data={name:b"verified asset" for name in FILES}
        data["index.html"]=html
        data["release.json"]=json.dumps({
            "release_id":"dp-hit-est-20261111-r1",
            "asset_blob_sha1":{p:git_blob_digest(data[p]) for p in FILES if p!="release.json"}
        }).encode()
        return data

    def test_current_local_manifest_pins_all_exact_source_files(self):
        local=self.files()
        self.assertEqual(validate_manifest(local),[])

    def test_manifests_must_change_with_updated_ui(self):
        local=self.files()
        local["index.html"]=local["index.html"]+b" updated"
        self.assertIn("index.html: LOCAL_MANIFEST_FILE_HASH_MISMATCH",
                      validate_manifest(local))

    def test_current_public_bytes_are_verified(self):
        local=self.files()
        actual={**local,"folder-root.html":local["index.html"]}
        self.assertEqual(evaluate(local,actual),[])

    def test_stale_phone_page_cannot_pass_repository_only_unit_test(self):
        local=self.files()
        remote={**local,"index.html":b"Sim est. SIM EST. old deployment"}
        reasons=inspect(local,remote)
        self.assertIn("index.html: PUBLIC_FILE_DIFFERS_FROM_CHECKED_OUT_MAIN",reasons)
        self.assertIn("PUBLIC_OLD_SIM_ESTIMATE_LABEL",reasons)

    def test_css_and_js_file_changes_are_hard_failures(self):
        local=self.files()
        for name in ("feeds.js","live_direct.js","dames_take.js","provisional.js","short_history.js"):
            remote=dict(local)
            remote[name]=b"old cached JavaScript"
            self.assertIn(name+": PUBLIC_FILE_DIFFERS_FROM_CHECKED_OUT_MAIN",
                          inspect(local,remote))

    def test_mismatched_release_manifest_fails(self):
        local=self.files()
        remote=dict(local)
        remote["release.json"]=json.dumps({"release_id":"old"}).encode()
        self.assertIn("RELEASE_ID_MISMATCH",inspect(local,remote))

    def test_cached_folder_root_fails_even_when_explicit_index_is_current(self):
        local=self.files()
        remote={**local,"folder-root.html":b"stale cached index"}
        self.assertIn("PUBLIC_FOLDER_ROOT_IS_STALE",evaluate(local,remote))

    def test_missing_files_fail_closed(self):
        local=self.files()
        remote={k:v for k,v in local.items() if k!="feeds.js"}
        self.assertIn("feeds.js: PUBLIC_FILE_UNAVAILABLE",inspect(local,remote))


class PhoneRuntimeBundleTests(unittest.TestCase):
    """Static release contract; a real mobile browser deployment gate is still required."""

    def test_executing_asset_identity_and_cache_key_for_every_bundle(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[2] / "docs" / "dames-picks"
        manifest = json.loads((root / "release.json").read_text())
        version = manifest["release_id"]
        self.assertEqual(version, manifest["runtime_bundle_id"])
        html = (root / "index.html").read_text()
        self.assertIn("activeScriptsCorrect", html)
        self.assertIn("runtime[name]===RELEASE_ID", html)
        self.assertIn("latest?.runtime_bundle_id===RELEASE_ID", html)
        for filename in ("feeds.js", "live_direct.js", "dames_take.js", "provisional.js","short_history.js"):
            self.assertIn('src="' + filename + '?bundle=' + version + '"', html)
            source = (root / filename).read_text()
            self.assertIn('globalThis.__damesRunningAssets[' + json.dumps(filename) + ']=' + json.dumps(version), source)

    def test_phone_verifier_fails_closed_when_runtime_bundle_missing_or_stale(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[2] / "docs" / "dames-picks"
        version = json.loads((root / "release.json").read_text())["release_id"]
        required = ("feeds.js", "live_direct.js", "dames_take.js", "provisional.js","short_history.js")
        def matches(runtime, script_urls):
            return all(runtime.get(name) == version and
                       name + "?bundle=" + version in script_urls
                       for name in required)
        urls = {name + "?bundle=" + version for name in required}
        runtime = dict.fromkeys(required, version)
        self.assertTrue(matches(runtime, urls))
        for name in required:
            stale = dict(runtime)
            stale[name] = "old-release"
            self.assertFalse(matches(stale, urls))
            missing = dict(runtime)
            missing.pop(name)
            self.assertFalse(matches(missing, urls))
            self.assertFalse(matches(runtime, urls - {name + "?bundle=" + version}))


if __name__=="__main__":
    unittest.main()

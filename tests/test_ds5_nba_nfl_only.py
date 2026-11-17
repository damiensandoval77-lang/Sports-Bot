"""Regression guard: DS5 serves NBA and NFL only, with no retired provider jobs."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs" / "dames-picks"

class NBAAndNFLOnly(unittest.TestCase):
    def test_canonical_runtime_and_previews_have_no_retired_sport(self):
        paths = [
            "index.html", "classic.html", "unified-shell.js",
            "concept-3-connected.js", "concept-3-connected.html",
            "concept-3-preview.html", "feeds.js", "live_direct.js",
            "dames_take.js", "provisional.js", "short_history.js",
            "release.json", "browser_readiness.json"
        ]
        for filename in paths:
            with self.subTest(file=filename):
                self.assertNotIn("tennis", (PUBLIC / filename).read_text(
                    encoding="utf-8").lower())

    def test_all_public_sport_tabs_and_workspaces_are_nba_nfl_only(self):
        classic = (PUBLIC / "classic.html").read_text(encoding="utf-8")
        shell = (PUBLIC / "unified-shell.js").read_text(encoding="utf-8")
        connected = (PUBLIC / "concept-3-connected.js").read_text(encoding="utf-8")
        self.assertIn('data-league="NBA"', classic)
        self.assertIn('data-league="NFL"', classic)
        self.assertEqual(classic.count('data-league="'), 2)
        self.assertIn('["NBA","NFL"]', connected)
        for mode in ("player", "board", "live", "tracker", "saved"):
            self.assertIn(mode, shell)
        self.assertNotIn('getJSON("tennis_board.json")', classic)

    def test_no_retired_models_provider_jobs_or_public_data(self):
        paths = [
            ".github/workflows/tennis-coverage-inspect.yml",
            ".github/workflows/tennis-provider-probe.yml",
            "docs/dames-picks/tennis.js",
            "docs/tennis_board.json",
            "docs/tennis_fixtures.json",
            "docs/tennis",
            "iphone_bot/probe_tennis_coverage.py",
            "iphone_bot/probe_tennis_provider.py",
            "src/cli/tennis_cli.py",
            "src/sports/tennis",
            "models/tennis",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists(), path)

    def test_release_bundle_matches_actual_files(self):
        release = json.loads((PUBLIC / "release.json").read_text())
        self.assertEqual(release["release_id"], "dp-nba-nfl-only-20261117-r53")
        self.assertEqual(release["runtime_bundle_id"], release["release_id"])
        expected = ("classic.html", "feeds.js", "live_direct.js",
                    "dames_take.js", "provisional.js", "short_history.js")
        self.assertEqual(set(release["asset_blob_sha1"]), set(expected))
        for name in expected:
            blob = (PUBLIC / name).read_bytes()
            sha = hashlib.sha1(
                f"blob {len(blob)}".encode("ascii") + bytes([0]) + blob
            ).hexdigest()
            self.assertEqual(release["asset_blob_sha1"][name], sha, name)
        self.assertNotIn("tennis", json.dumps(release).lower())

if __name__ == "__main__":
    unittest.main()

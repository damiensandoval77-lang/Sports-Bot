"""Offline snapshot safeguards; no external network or sportsbook dependency."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

try:
    from iphone_bot.external_stats_snapshot import load_snapshot, SnapshotError
except ImportError:
    from external_stats_snapshot import load_snapshot, SnapshotError


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.csv = root / "players.csv"
        self.manifest = root / "manifest.json"
        self.csv.write_text("NAME,TEAM,GP,MpG,USG%,PpG,RpG,ApG\nExample Player,BOS,10,33.8,25,22,5,6\n", encoding="utf-8")
        self.meta = {"source_name": "authorized export", "source_url": "https://example.com/data",
                     "season": "2026-2027", "as_of": "2026-11-09",
                     "rights_confirmed": True, "research_only": True}
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.meta), encoding="utf-8")

    def load(self):
        return load_snapshot(self.csv, self.manifest, "player", today=date(2026, 11, 9))

    def test_valid_research_only(self):
        result = self.load()
        self.assertEqual(result["rows"][0]["USG%"], 25.0)
        self.assertFalse(result["production_modified"])
        self.assertFalse(result["position_defense_verified"])
        self.assertFalse(result["calibrated"])

    def test_unconfirmed_rights_rejected(self):
        self.meta["rights_confirmed"] = False
        self.save()
        with self.assertRaises(SnapshotError):
            self.load()

    def test_stale_rejected(self):
        self.meta["as_of"] = "2026-11-01"
        self.save()
        with self.assertRaises(SnapshotError):
            self.load()

    def test_duplicate_rejected(self):
        self.csv.write_text(self.csv.read_text() + "Example Player,BOS,10,32,25,20,4,6\n")
        with self.assertRaises(SnapshotError):
            self.load()

    def test_bad_numeric_rejected(self):
        self.csv.write_text(self.csv.read_text().replace(",25,22", ",nan,22"))
        with self.assertRaises(SnapshotError):
            self.load()

    def test_missing_columns_rejected(self):
        self.csv.write_text("NAME,TEAM,GP\nExample,BOS,10\n")
        with self.assertRaises(SnapshotError):
            self.load()

    def test_team_snapshot(self):
        self.csv.write_text("TEAM,GP,PACE,oEFF,dEFF\nBoston,10,95.2,119.6,108.5\n")
        result = load_snapshot(self.csv, self.manifest, "team", today=date(2026,11,9))
        self.assertEqual(result["rows"][0]["PACE"], 95.2)


if __name__ == "__main__":
    unittest.main()

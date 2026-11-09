"""Offline checks for the non-mutating NFL reliability gate."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_nfl_reliability import audit


class TestAudit(unittest.TestCase):
    def make_data(self, root):
        folder = root / "boxscores"
        folder.mkdir(parents=True)
        games = [{"game_id": f"game{i}", "status": "final" if i < 4 else "scheduled"} for i in range(272)]
        (root / "schedule_2026.json").write_text(json.dumps({"game_count": 272, "games": games}))
        (root / "latest_2026.json").write_text(json.dumps({"rows": 5, "captured_at": "2026-11-09T19:00:00Z", "files": ["latest_2026_00.csv"]}))
        with (root / "latest_2026_00.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["captured_at", "game_id"])
            writer.writeheader()
            writer.writerows([{"captured_at": "2026-11-09T19:00:00Z", "game_id": "game0"}] * 5)
        (root / "grading_health_2026.json").write_text(json.dumps({"archived_pregame_lines": 0, "graded_picks": 0, "pending_picks": 0, "expected_final_picks": 0}))
        for name in ["frozen_pick_history_2026.csv", "pp_graded_2026.csv", "pp_grading_pending_2026.csv"]:
            (root / name).write_text("game_id,grade_status\n")
        (folder / "manifest.json").write_text(json.dumps({"season": 2026, "games_with_stats": 4}))

    def test_zero_grades_not_automatically_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_data(root)
            self.assertEqual(audit(root)["status"], "HEALTHY")

    def test_final_pregame_quote_missing_from_grades_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_data(root)
            schedule = json.loads((root / "schedule_2026.json").read_text())
            schedule["games"][0].update(home_score=10, away_score=7)
            (root / "schedule_2026.json").write_text(json.dumps(schedule))
            with (root / "frozen_pick_history_2026.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "captured_at", "game_id", "player_id", "target",
                    "odds_type", "line", "pick"])
                writer.writeheader()
                writer.writerow({"captured_at": "2026-11-09T19:00:00Z",
                                 "game_id": "game0", "player_id": "p1",
                                 "target": "REC_YDS", "odds_type": "standard",
                                 "line": "50.5", "pick": "More"})
            health = json.loads((root / "grading_health_2026.json").read_text())
            health["archived_pregame_lines"] = 1
            (root / "grading_health_2026.json").write_text(json.dumps(health))
            result = audit(root)
            self.assertEqual(result["status"], "FAILED")
            self.assertEqual(result["missing_final_pick_grades"], 1)

    def test_pending_final_quote_counts_as_accounted_for(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_data(root)
            schedule = json.loads((root / "schedule_2026.json").read_text())
            schedule["games"][0].update(home_score=10, away_score=7)
            (root / "schedule_2026.json").write_text(json.dumps(schedule))
            item = {"captured_at": "2026-11-09T19:00:00Z",
                    "game_id": "game0", "player_id": "p1",
                    "target": "REC_YDS", "odds_type": "standard",
                    "line": "50.5", "pick": "More"}
            with (root / "frozen_pick_history_2026.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(item))
                writer.writeheader()
                writer.writerow(item)
            item["grade_status"] = "boxscore_not_yet_published"
            with (root / "pp_grading_pending_2026.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(item))
                writer.writeheader()
                writer.writerow(item)
            health = json.loads((root / "grading_health_2026.json").read_text())
            health.update(archived_pregame_lines=1, pending_picks=1,
                          expected_final_picks=1)
            (root / "grading_health_2026.json").write_text(json.dumps(health))
            result = audit(root)
            self.assertEqual(result["status"], "HEALTHY")
            self.assertEqual(result["eligible_frozen_final_picks"], 1)

    def test_missing_snapshot_chunk_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_data(root)
            (root / "latest_2026_00.csv").unlink()
            self.assertEqual(audit(root)["status"], "FAILED")

    def test_grading_count_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_data(root)
            (root / "pp_graded_2026.csv").write_text("game_id,grade_status\ngame0,graded\n")
            self.assertEqual(audit(root)["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()

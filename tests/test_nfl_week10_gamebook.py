"""Reviewed Week 10 end-to-end source evidence and unusual scoring."""
import json
from pathlib import Path
import sys
import unittest
from copy import deepcopy
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verified_nfl_gamebook as v
import reconcile_nfl_picks as r

ROOT = Path(__file__).resolve().parents[1] / "docs/nfl/data"
SCHEDULE = {x["game_id"]: x for x in json.loads((ROOT / "schedule_2026.json").read_text())["games"]}

def evidence(gid):
    return json.loads((ROOT / "boxscores" / f"verified_gamebook_{gid}.json").read_text())

class ReviewedWeek10(unittest.TestCase):
    def test_each_new_game_reconciles_to_exact_final(self):
        self.assertEqual(len(v.REVIEWED_GAMES), 13)
        for gid in v.REVIEWED_GAMES:
            with self.subTest(gid=gid):
                self.assertGreater(len(v.validate(evidence(gid), SCHEDULE[gid])), 0)

    def test_two_point_participants_and_qb_provider_hold(self):
        gid = "2026_10_PIT_CIN"
        data = evidence(gid)
        scoring = data["verified_game_scoring"]
        rows = {p["player"]: p for p in v.validate(data, SCHEDULE[gid])}
        for name in ("DK Metcalf", "Aaron Rodgers"):
            self.assertAlmostEqual(v.fantasy(rows[name], scoring) - v.fantasy(rows[name]), 2)
        boxes, _ = r.verified_boxscores(SCHEDULE, ROOT / "boxscores")
        qb = boxes[gid][rows["Aaron Rodgers"]["player_id"]]
        self.assertIn("FPTS", qb["excluded_recovery_targets"])
        invalid = deepcopy(data)
        bad = invalid["verified_game_scoring"]["two_point_conversions"][0]
        bad["player_ids"][0] = next(row["player_id"] for row in rows.values() if row["team"] != bad["team"])
        with patch.dict(v.REVIEWED_GAMES, {gid: {**v.REVIEWED_GAMES[gid], "sha": v.digest(invalid)}}):
            with self.assertRaisesRegex(ValueError, "attribution"):
                v.validate(invalid, SCHEDULE[gid])

    def test_defense_counts_to_team_score_only(self):
        gid = "2026_10_MIA_IND"
        data = evidence(gid)
        self.assertEqual([6, 6], [x["points"] for x in data["verified_game_scoring"]["defensive_scores"]])
        for p in v.validate(data, SCHEDULE[gid]):
            self.assertEqual(v.fantasy(p, data["verified_game_scoring"]), v.fantasy(p))
        bad = deepcopy(data)
        bad["verified_game_scoring"]["defensive_scores"].pop()
        with patch.dict(v.REVIEWED_GAMES, {gid: {**v.REVIEWED_GAMES[gid], "sha": v.digest(bad)}}):
            with self.assertRaisesRegex(ValueError, "final scoring"):
                v.validate(bad, SCHEDULE[gid])

if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from iphone_bot.defender_matchup_v3 import (
    clean_matchup,defender_scenario,research_status)


def row(defender="21",poss=100,fga=40,fgm=12,off="10"):
    return {"OFF_PLAYER_ID":off,"DEF_PLAYER_ID":defender,"PARTIAL_POSS":poss,
        "MATCHUP_FGA":fga,"MATCHUP_FGM":fgm,"MATCHUP_MIN":35}


def scenario(rows=None,**changes):
    args={"off_id":"10","opponent_defender_ids":["21","22"],
      "rows":rows if rows is not None else [row()],
      "offense_fg_pct":.5,"baseline_points":25.0,
      "as_of":"2026-11-07T00:00:00Z",
      "source_through":"2026-11-06T00:00:00Z",
      "rotation_verified":True}
    args.update(changes)
    return defender_scenario(**args)


class DefenderV3ResearchTests(unittest.TestCase):
    def test_exposure_weighted_shrunken_defense_no_fake_confirmation(self):
        result=scenario([row("21",100,40,12),row("22",100,40,28)])
        self.assertEqual(result["status"],"DEFENDER_RESEARCH_SCENARIO_ONLY")
        self.assertEqual(len(result["defenders"]),2)
        self.assertEqual(sum(x["historical_exposure_share"] for x in result["defenders"]),1.0)
        self.assertTrue(all(not x["confirmed_primary_defender"] for x in result["defenders"]))
        self.assertFalse(result["live_applied"])
        self.assertFalse(result["validated_for_live_use"])
        self.assertLessEqual(abs(result["adjustment_points"]),2.0)

    def test_rotation_unverified_no_projection(self):
        result=scenario(rotation_verified=False)
        self.assertEqual(result["status"],"OPPONENT_ROTATION_UNVERIFIED")
        self.assertIsNone(result["projection"])

    def test_source_date_cannot_leak_target_game(self):
        for through in ("2026-11-07T00:00:00Z","2026-11-08T00:00:00Z"):
            result=scenario(source_through=through)
            self.assertEqual(result["status"],"SOURCE_NOT_STRICTLY_PREGAME")
            self.assertIsNone(result["projection"])

    def test_insufficient_data_rejected(self):
        result=scenario([row(poss=35,fga=10,fgm=1)])
        self.assertEqual(result["status"],"INSUFFICIENT_HISTORICAL_MATCHUP_SAMPLE")
        self.assertIsNone(result["projection"])

    def test_only_verified_opponent_defenders_and_same_offender(self):
        result=scenario([row("999",1000,300,0),row("21",100,40,12),
                         row("22",100,40,24,off="999")])
        self.assertEqual(len(result["defenders"]),1)
        self.assertEqual(result["defenders"][0]["def_player_id"],"21")

    def test_malformed_counts_and_ids_never_contribute(self):
        self.assertIsNone(clean_matchup(row(fga=200)))
        self.assertIsNone(clean_matchup(row(fga=20,fgm=25)))
        self.assertIsNone(clean_matchup(row(defender="unknown")))
        self.assertIsNone(clean_matchup(row(off="21",defender="21")))

    def test_missing_source_is_explicit_and_does_not_modify_live_predictions(self):
        with tempfile.TemporaryDirectory() as dirname:
            output=Path(dirname)/"research.json"
            report=research_status(Path(dirname)/"not-yet-available.json",output)
            self.assertEqual(report["status"],"AWAITING_VERIFIED_NBA_DEFENDER_MATCHUP_SOURCE")
            self.assertFalse(report["defender_assignments_confirmed"])
            self.assertTrue(report["live_model_unchanged"])
            self.assertTrue(output.exists())


if __name__=="__main__":unittest.main()

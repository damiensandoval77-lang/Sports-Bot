import unittest
from iphone_bot.reliability_screen import research_screen

def row(**overrides):
    baseline = {
        "line":20.5, "stat":"PTS", "combined_projection":24,
        "projection":23, "shadow_projection":25,
        "shadow_status":"RESEARCH_SHADOW_ONLY", "sample_games":8,
        "injury_status":"NOT_VERIFIED",
        "injury_status_source":"UNAVAILABLE_OR_NOT_GAME_DAY",
        "injury_reprojection_status":"NO_OFFICIAL_OUT_IN_MATCHUP",
        "combined_simulation":{"simulation_count":20000,
            "selected_hit_rate":0.61,"direction":"Over","calibrated":False}
    }
    baseline.update(overrides)
    return baseline

class ResearchReliabilityScreenTests(unittest.TestCase):
    def test_model_lean_with_early_season_and_unlisted_player(self):
        result=research_screen(row())
        self.assertEqual(result["status"],"MODEL_LEAN")
        self.assertEqual(result["side"],"MORE")
        self.assertIn("EARLY_SEASON_SHORT_HISTORY",result["cautions"])
        self.assertIn("OFFICIAL_PLAYER_STATUS_NOT_CONFIRMED",result["cautions"])
        self.assertFalse(result["validated"])
        self.assertFalse(result["wager_recommended"])

    def test_disagreement_is_a_pass(self):
        result=research_screen(row(projection=19,shadow_projection=25))
        self.assertIn("MODELS_DISAGREE_OR_TIE",result["blockers"])
        self.assertEqual(result["status"],"PASS")

    def test_fewer_than_five_games_is_a_pass(self):
        result=research_screen(row(sample_games=4))
        self.assertIn("INSUFFICIENT_RECENT_PLAYER_GAMES",result["blockers"])

    def test_questionable_or_out_is_a_pass(self):
        for status in ("OUT","QUESTIONABLE","DOUBTFUL"):
            with self.subTest(status=status):
                self.assertEqual(research_screen(row(injury_status=status))["status"],"PASS")

    def test_unvalidated_injury_adjustment_gets_caution_not_blanket_abstain(self):
        result=research_screen(row(injury_reprojection_status="REPROJECTED_FROM_VERIFIED_OFFICIAL_OUT"))
        self.assertEqual(result["status"],"MODEL_LEAN")
        self.assertIn("UNVALIDATED_INJURY_ADJUSTMENT",result["cautions"])

    def test_missing_simulation_does_not_fabricate_probabilities(self):
        result=research_screen(row(combined_simulation=None))
        self.assertEqual(result["status"],"MODEL_LEAN")
        self.assertIn("UNVALIDATED_OR_UNAVAILABLE_COMBINED_SIMULATION",result["cautions"])

    def test_tiny_projection_gap_passes(self):
        result=research_screen(row(combined_projection=21.0,projection=21.1,shadow_projection=20.9))
        self.assertEqual(result["status"],"PASS")
        self.assertIn("SMALL_PROJECTION_EDGE",result["blockers"])

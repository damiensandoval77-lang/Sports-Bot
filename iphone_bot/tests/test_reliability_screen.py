import unittest
from iphone_bot.reliability_screen import research_screen

def row(**overrides):
    result={
        "line":20.5,"combined_projection":24,"projection":23,
        "shadow_projection":25,"shadow_status":"RESEARCH_SHADOW_ONLY",
        "sample_games":30,"injury_status_source":"OFFICIAL_NBA_REPORT",
        "injury_reprojection_status":"NO_OFFICIAL_OUT_IN_MATCHUP",
        "combined_simulation":{"simulation_count":20000,"selected_hit_rate":0.61}
    }
    result.update(overrides)
    return result

class ResearchReliabilityScreenTests(unittest.TestCase):
    def test_no_structural_flags_is_still_unvalidated(self):
        result=research_screen(row())
        self.assertEqual(result["status"],"RESEARCH_ONLY")
        self.assertFalse(result["validated"])
        self.assertFalse(result["wager_recommended"])
    def test_disagreement_abstains(self):
        result=research_screen(row(projection=19,shadow_projection=25))
        self.assertIn("ORIGINAL_OPPONENT_DISAGREE",result["reasons"])
        self.assertEqual(result["status"],"ABSTAIN")
    def test_absent_history_and_official_availability_abstains(self):
        result=research_screen(row(sample_games=5,injury_status_source="UNAVAILABLE_OR_NOT_GAME_DAY"))
        self.assertIn("SHORT_PLAYER_HISTORY",result["reasons"])
        self.assertIn("PLAYER_AVAILABILITY_NOT_OFFICIALLY_VERIFIED",result["reasons"])
    def test_injury_adjustment_not_promoted(self):
        result=research_screen(row(injury_reprojection_status="REPROJECTED_FROM_VERIFIED_OFFICIAL_OUT"))
        self.assertEqual(result["status"],"ABSTAIN")
    def test_simulation_missing_not_fabricated(self):
        result=research_screen(row(combined_simulation=None))
        self.assertIn("COMBINED_SIMULATION_UNAVAILABLE",result["reasons"])

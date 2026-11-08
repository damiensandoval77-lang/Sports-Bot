"""Actual pregame injury-reprojection guards; no outcomes or fake availability."""
import unittest
from iphone_bot.injury_projection_adjustment import (
    teammate_minutes_ratio,opponent_defense_ratio,reproject)


class InjuryProjectionAdjustmentTests(unittest.TestCase):
    def test_official_teammate_out_updates_original_and_combined(self):
        scenario={"status":"HISTORICAL_SCENARIO_RESEARCH_ONLY",
                  "baseline_minutes":30,"scenario_minutes":33,
                  "with_games":5,"without_games":4}
        factor=teammate_minutes_ratio(scenario,1)
        self.assertAlmostEqual(factor,1.1)
        updated=reproject(20,24,factor,1)
        self.assertAlmostEqual(updated["original"],22)
        self.assertAlmostEqual(updated["opponent"],26.4)
        self.assertAlmostEqual(updated["combined"],24.2)
        self.assertEqual(teammate_minutes_ratio(scenario,0),1)
        self.assertIsNone(teammate_minutes_ratio(scenario,2))
        self.assertIsNone(teammate_minutes_ratio({**scenario,"without_games":2},1))

    def test_opponent_out_with_prior_on_off_sample_reprojects(self):
        allowed={"WAS":[
            (f"2026-10-{i:02d}",{"PTS":100 if i<4 else 120,
                                   "REB":40,"AST":25,"PRA":165 if i<4 else 185})
            for i in range(1,7)]}
        games=[{"id":"203076","team":"WAS","date":f"2026-10-{i:02d}","MIN":34}
               for i in range(1,4)]
        factor=opponent_defense_ratio(allowed,"WAS",["203076"],games,"2026-11-07","PTS")
        self.assertAlmostEqual(factor,1.07)
        updated=reproject(25,27,1,factor)
        self.assertAlmostEqual(updated["combined"],27.82)
        # Data from the target game must never be consumed.
        games.append({"id":"203076","team":"WAS","date":"2026-11-07","MIN":45})
        self.assertEqual(factor,opponent_defense_ratio(
            allowed,"WAS",["203076"],games,"2026-11-07","PTS"))

    def test_missing_opponent_sample_does_not_publish_old_projection_as_adjusted(self):
        allowed={"WAS":[("2026-10-01",{"PTS":110})]}
        self.assertIsNone(opponent_defense_ratio(
            allowed,"WAS",["203076"],[],"2026-11-07","PTS"))
        self.assertIsNone(reproject(20,23,None,1))
        self.assertIsNone(reproject(20,23,1,None))

    def test_unaffected_player_stays_at_original_model_number(self):
        r=reproject(20,24,1,1)
        self.assertEqual(r["original"],20)
        self.assertEqual(r["combined"],22)
        self.assertEqual(r["factor"],1)

if __name__=="__main__":
    unittest.main()

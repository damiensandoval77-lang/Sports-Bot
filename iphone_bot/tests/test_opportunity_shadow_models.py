import unittest
from iphone_bot.opportunity_shadow_models import forecast_opportunity,backtest_opportunity

def examples():
    tracking={("123","NYK"):[
        {"date":f"2026-11-{d:02d}","potential_assists":float(p),
         "rebound_chances":float(r)}
        for d,p,r in [(1,10,13),(2,12,15),(3,14,16),(4,16,18),
                      (5,80,80)]]}
    boxes=[{"id":"123","team":"NYK","date":f"2026-11-{d:02d}",
            "AST":ast,"REB":reb,"MIN":mins}
           for d,ast,reb,mins in [(1,5,8,30),(2,6,9,30),(3,7,10,30),
                                   (4,8,11,30),(5,40,40,30)]]
    return tracking,boxes

class TrackingOpportunityModelTests(unittest.TestCase):
    def test_assist_and_rebound_candidates_are_independent(self):
        data,boxes=examples()
        p=forecast_opportunity(data,"123","NYK","2026-11-05",boxes,30)
        self.assertEqual(p["AST"]["status"],"PREGAME_OPPORTUNITY_SHADOW")
        self.assertEqual(p["REB"]["status"],"PREGAME_OPPORTUNITY_SHADOW")
        self.assertGreater(p["AST"]["projection"],0)
        self.assertGreater(p["REB"]["projection"],0)
        self.assertEqual(p["AST"]["latest_paired_game"],"2026-11-04")
        self.assertEqual(p["REB"]["latest_paired_game"],"2026-11-04")
        self.assertFalse(p["AST"]["production_applied"])
        self.assertFalse(p["REB"]["production_applied"])

    def test_no_future_game_leakage(self):
        data,boxes=examples()
        before=forecast_opportunity(data,"123","NYK","2026-11-05",
                                    boxes[:4],30)
        after=forecast_opportunity(data,"123","NYK","2026-11-05",boxes,30)
        self.assertEqual(before["AST"]["projection"],after["AST"]["projection"])
        self.assertEqual(before["REB"]["projection"],after["REB"]["projection"])

    def test_missing_tracking_is_not_estimated(self):
        _,boxes=examples()
        p=forecast_opportunity({},"123","NYK","2026-11-05",boxes,30)
        self.assertIsNone(p["AST"]["projection"])
        self.assertIsNone(p["REB"]["projection"])

    def test_mismatched_player_and_team_not_paired(self):
        tracking,boxes=examples()
        bad=[dict(x,team="BOS") for x in boxes]
        result=forecast_opportunity(tracking,"123","NYK","2026-11-05",bad,30)
        self.assertEqual(result["AST"]["status"],"INSUFFICIENT_TRACKED_GAMES")

    def test_chronological_backtest_uses_same_actual_game(self):
        tracking,boxes=examples()
        result=backtest_opportunity(tracking,boxes)
        self.assertGreater(result["by_market"]["AST"]["paired_player_games"],0)
        self.assertGreater(result["by_market"]["REB"]["paired_player_games"],0)
        self.assertFalse(result["production_applied"])

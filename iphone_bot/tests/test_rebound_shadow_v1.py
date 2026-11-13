import unittest
from iphone_bot.rebound_shadow_v1 import forecast

def history(rebounds=8.0):
    return [{"id":"10","team":"BOS","date":f"2026-10-{d:02d}",
             "MIN":30.0,"REB":rebounds} for d in range(15,25)]

class ReboundShadowTests(unittest.TestCase):
    def test_strictly_prior_minutes_normalized_rebound_forecast(self):
        r=forecast(history(),team="BOS",event_date="2026-11-07",
                   baseline=6,expected_minutes=30)
        self.assertEqual(r["status"],"PRETIP_REBOUND_OPPORTUNITY_SHADOW")
        self.assertEqual(r["prior_games"],10)
        self.assertEqual(r["prior_latest_game"],"2026-10-24")
        self.assertEqual(r["projection"],6.6)
        self.assertFalse(r["live_applied"])
        self.assertFalse(r["probability_calibrated"])
        self.assertEqual(r["predicted_minutes"],30)
    def test_no_future_game_leakage_and_other_team_ignored(self):
        past=history()
        expected=forecast(past,team="BOS",event_date="2026-11-07",
                          baseline=7,expected_minutes=32)
        past+=[{"team":"BOS","date":"2026-11-07","MIN":35,"REB":55},
               {"team":"BOS","date":"2026-11-09","MIN":35,"REB":55},
               {"team":"NYK","date":"2026-10-25","MIN":35,"REB":55}]
        self.assertEqual(expected["projection"],forecast(past,team="BOS",
            event_date="2026-11-07",baseline=7,expected_minutes=32)["projection"])
    def test_volatility_and_coverage_fail_closed(self):
        small=forecast(history()[:6],team="BOS",event_date="2026-11-07",
                       baseline=7)
        self.assertEqual(small["status"],"INSUFFICIENT_PRIOR_GAMES")
        games=history()
        for i,x in enumerate(games[-5:]):
            x["MIN"]=[12,37,12,37,12][i]
        self.assertEqual(forecast(games,team="BOS",event_date="2026-11-07",
                        baseline=7)["status"],"UNSTABLE_MINUTES_ROLE")
    def test_duplicate_conflicting_day_cannot_add_games(self):
        games=history()[:8]
        games+=[{**games[-1],"REB":20}]
        self.assertEqual(forecast(games,team="BOS",event_date="2026-11-07",
                         baseline=7)["status"],"INSUFFICIENT_PRIOR_GAMES")
    def test_no_missing_rate_or_false_win_probability(self):
        games=history()
        games[-1]["REB"]=None
        result=forecast(games,team="BOS",event_date="2026-11-07",
                        baseline=6,expected_minutes=32)
        self.assertEqual(result["prior_games"],9)
        self.assertIsNotNone(result["projection"])
        self.assertNotIn("hit_probability",result)

if __name__=="__main__": unittest.main()

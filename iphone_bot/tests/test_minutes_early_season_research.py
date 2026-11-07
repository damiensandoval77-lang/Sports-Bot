import unittest
from iphone_bot.minutes_early_season_research import forecast,backtest,METHOD

def g(player,day,minutes,team="BOS"):
    return {"id":str(player),"date":f"2026-10-{day:02d}","team":team,"MIN":float(minutes)}

class MinutesEarlySeasonTests(unittest.TestCase):
    def test_exactly_five_prior_games_is_research_only(self):
        history=[g(1,d,20+d) for d in range(1,6)]
        r=forecast(history,"2026-10-06","BOS")
        self.assertEqual(r["status"],"RESEARCH_FORECAST_UNVALIDATED")
        self.assertEqual(r["history_games"],5)
        self.assertEqual(r["history_confidence"],"LIMITED_5_TO_7_GAMES")
        self.assertGreater(r["expected_minutes"],0)
        self.assertFalse(r["production_applied"])
        self.assertEqual(r["method"],METHOD)
    def test_future_and_other_team_never_leak(self):
        history=[g(1,d,29) for d in range(1,8)]
        before=forecast(history,"2026-10-08","BOS")
        modified=forecast(history+[g(1,8,58),g(1,7,50,"MIA")],
                          "2026-10-08","BOS")
        self.assertEqual(before,modified)
    def test_nonfinite_and_conflicting_duplicates_fail_closed(self):
        rows=[g(1,d,24) for d in range(1,7)]
        rows.append(g(1,4,55))
        rows.append(g(1,7,float("nan")))
        r=forecast(rows,"2026-10-08","BOS")
        self.assertEqual(r["history_games"],5)
        self.assertTrue(0<=r["expected_minutes"]<=48)
    def test_chronological_holdout_has_no_same_date_overlap(self):
        games=[g(p,d,28+(p%5)+(d%2)) for p in range(12)
               for d in range(1,12)]
        r=backtest(games,minimum_test=12,minimum_dates=3)
        self.assertEqual(r["status"],"DESCRIPTIVE_CHRONOLOGICAL_HOLDOUT")
        self.assertEqual(r["holdout_start"],"2026-10-10")
        self.assertGreater(r["holdout_samples"],0)
        self.assertIsNotNone(r["candidate_minus_baseline_mae"])
        self.assertFalse(r["validated_for_production"])
    def test_empty_data_has_no_fake_validation(self):
        r=backtest([])
        self.assertIsNone(r["candidate_mae"])
        self.assertEqual(r["status"],"INSUFFICIENT_CHRONOLOGICAL_SAMPLES")
if __name__=="__main__":unittest.main()

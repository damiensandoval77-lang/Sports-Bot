"""Research-only robust minutes forecasts: no future leakage or live changes."""
import unittest
from iphone_bot.minutes_model_v2 import forecast,backtest,player_history


def game(player,day,minutes,team="BOS"):
    return {"id":str(player),"date":f"2026-10-{day:02d}",
            "team":team,"MIN":minutes}


class MinutesModelV2Tests(unittest.TestCase):
    def test_future_games_and_other_teams_are_excluded(self):
        past=[game(1,d,30) for d in range(1,10)]
        base=forecast(past,"2026-10-10","BOS")
        outliers=past+[game(1,12,57),game(1,8,58,"MIA")]
        checked=forecast(outliers,"2026-10-10","BOS")
        self.assertEqual(base["expected_minutes"],checked["expected_minutes"])
        self.assertEqual(checked["history_games"],9)
        self.assertFalse(checked["live_adjustment_applied"])
        self.assertFalse(checked["confirmed_lineup"])

    def test_robust_candidate_differs_on_high_variance(self):
        history=[game(1,d,v) for d,v in enumerate(
            [30,30,30,30,30,30,30,8,40,12],start=1)]
        res=forecast(history,"2026-10-11","BOS")
        self.assertEqual(res["status"],"RESEARCH_FORECAST_UNVALIDATED")
        self.assertGreater(res["last5_volatility"],6)
        self.assertGreater(res["expected_minutes"],0)
        self.assertLessEqual(res["expected_minutes"],48)

    def test_insufficient_and_invalid_minutes_not_used(self):
        rows=[game(1,d,30) for d in range(1,8)]
        self.assertIsNone(forecast(rows,"2026-10-08","BOS")["expected_minutes"])
        rows.append(game(1,8,float("nan")))
        self.assertIsNone(forecast(rows,"2026-10-09","BOS")["expected_minutes"])
        rows.append(game(1,9,30))
        self.assertEqual(forecast(rows,"2026-10-10","BOS")["history_games"],8)

    def test_conflicting_same_day_minutes_cannot_be_restored_by_later_duplicate(self):
        # A repeated conflicting feed row must never turn an ambiguous
        # player-day into a usable pregame observation.
        stable=[game(1,d,30) for d in range(2,9)]
        for duplicate_order in ((30,42,30),(42,30,42),(30,30,42,30)):
            with self.subTest(duplicate_order=duplicate_order):
                rows=[game(1,1,value) for value in duplicate_order]+stable
                history=player_history(rows,"2026-10-09","BOS")
                self.assertEqual(len(history),7)
                self.assertNotIn("2026-10-01",[day for day,_ in history])
                forecasted=forecast(rows,"2026-10-09","BOS")
                self.assertEqual(forecasted["history_games"],7)
                self.assertIsNone(forecasted["expected_minutes"])

    def test_holdout_is_on_disjoint_dates_and_same_games(self):
        # 10 dates, 15 unique player observations on each date. V2 can
        # evaluate from date 9; 30 same-game predictions on two dates.
        games=[game(p,d,27+(p%5)+(1 if d%2 else -1))
               for p in range(15) for d in range(1,11)]
        result=backtest(games,minimum_test=10,minimum_dates=2)
        self.assertEqual(result["status"],"CHRONOLOGICAL_RESEARCH_HOLDOUT")
        self.assertEqual(result["holdout_samples"],15)
        self.assertEqual(result["earlier_samples"],15)
        self.assertEqual(result["holdout_start"],"2026-10-10")
        self.assertEqual(result["candidate_improved"]+
                         result["candidate_worsened"]+result["tied"],
                         result["holdout_samples"])
        self.assertFalse(result["production_adjustment_applied"])
        self.assertFalse(result["validated_for_production"])

    def test_outcome_changes_do_not_retroactively_change_earlier_results(self):
        games=[game(p,d,29) for p in range(15) for d in range(1,11)]
        original=backtest(games,minimum_test=10,minimum_dates=2)
        changed=games+[game(p,11,55) for p in range(15)]
        future=backtest(changed,minimum_test=10,minimum_dates=2)
        # holdout evaluation may expand with new completed dates, but the
        # old forecast function ignores future outcomes before as-of.
        before=forecast([g for g in changed if g["id"]=="0"],
                        "2026-10-10","BOS")
        expected=forecast([g for g in games if g["id"]=="0"],
                          "2026-10-10","BOS")
        self.assertEqual(before["expected_minutes"],expected["expected_minutes"])
        self.assertEqual(original["earlier_samples"],15)
        self.assertEqual(future["status"],"CHRONOLOGICAL_RESEARCH_HOLDOUT")


if __name__=="__main__":
    unittest.main()

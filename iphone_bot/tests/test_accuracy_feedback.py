"""Strict chronological feedback from saved, independently graded NBA forecasts."""
import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.accuracy_feedback import evaluate,eligible_rows,chronological_split


def record(day,player,actual,market="PTS",book="FanDuel",captured_shift=4):
    start=datetime(2026,10,1,23,0,tzinfo=timezone.utc)+timedelta(days=day)
    return {"status":"SETTLED","player_id":str(player),"team":"BOS",
            "market":market,"bookmaker":book,"event_start":start.isoformat(),
            "captured_at":(start-timedelta(hours=captured_shift)).isoformat(),
            "line":12.5,"actual":actual,"original_projection":10,
            "opponent_shadow_projection":14,"combined_projection":12,
            "side":"OVER","american_odds":-110}


class AccuracyFeedbackTests(unittest.TestCase):
    def dataset(self):
        # Eight entire days; 6 independently identified player/market
        # outcomes per date. First 5 dates (30 rows) train-side, final 3
        # dates (18 rows) later holdout.
        return [record(day,player,11 if day<5 else 13)
                for day in range(8) for player in range(6)]

    def test_full_date_holdout_and_identical_model_samples(self):
        results=evaluate(self.dataset())
        self.assertTrue(results["live_model_unchanged"])
        overall=results["overall"]
        self.assertEqual(overall["status"],"DESCRIPTIVE_CHRONOLOGICAL_HOLDOUT")
        self.assertEqual(overall["earlier"]["observations"],30)
        self.assertEqual(overall["later_holdout"]["observations"],18)
        self.assertLess(overall["earlier_end_date"],overall["later_start_date"])
        self.assertEqual(overall["overall"]["observations"],48)
        self.assertEqual(overall["later_holdout"]["mae"]["original"],3)
        self.assertEqual(overall["later_holdout"]["mae"]["opponent_aware"],1)
        self.assertEqual(overall["later_holdout"]["mae"]["combined"],1)
        self.assertIsNone(overall["heldout_better_model"])
        self.assertFalse(overall["validated_for_live_use"])

    def test_independent_books_same_prop_do_not_double_count(self):
        rows=self.dataset()
        extra=dict(rows[0],bookmaker="DraftKings",
                   captured_at="2026-10-01T20:00:00+00:00")
        results=evaluate(rows+[extra])
        self.assertEqual(results["overall"]["overall"]["observations"],48)

    def test_pending_late_nonfinite_and_incomplete_shadow_excluded(self):
        good=record(0,1,11)
        pending=dict(record(1,2,12),status="PENDING")
        late=record(2,3,12,captured_shift=-1)
        broken=dict(record(3,4,12),actual=float("nan"))
        no_shadow=dict(record(4,5,12),opponent_shadow_projection=None)
        out=eligible_rows([good,pending,late,broken,no_shadow])
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["player_id"],"1")

    def test_no_false_readiness_when_dates_are_few(self):
        data=[record(day,player,12) for day in range(2) for player in range(50)]
        self.assertIsNone(chronological_split(eligible_rows(data)))
        result=evaluate(data)["overall"]
        self.assertEqual(result["status"],"INSUFFICIENT_CHRONOLOGICAL_SAMPLE")
        self.assertIsNone(result["later_holdout"])
        self.assertFalse(result["validated_for_live_use"])

    def test_per_market_separation_and_signed_bias(self):
        rows=self.dataset()+[record(3,99,15,market="REB")]
        report=evaluate(rows)
        self.assertEqual(report["by_stat"]["REB"]["overall"]["observations"],1)
        self.assertEqual(report["by_stat"]["PTS"]["overall"]["observations"],48)
        self.assertEqual(report["by_stat"]["REB"]["overall"]["signed_bias"]["original"],-5)
        self.assertTrue(report["common_sample_only"])


if __name__=="__main__":
    unittest.main()

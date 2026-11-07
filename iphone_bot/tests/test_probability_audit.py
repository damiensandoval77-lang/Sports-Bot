import unittest
from iphone_bot.probability_audit import audit


def record(player="1",book="FanDuel",p=.72,actual=25,line=20.5,
           original=22,status="SETTLED",market="PTS",captured="2026-11-12T19:00:00Z"):
    return {"status":status,"event_start":"2026-11-13T00:30:00Z",
        "captured_at":captured,"player_id":player,"market":market,"bookmaker":book,
        "line":line,"actual":actual,"original_projection":original,
        "original_probability_side":"OVER" if original>line else "UNDER",
        "original_probability_estimate":p,
        "original_probability_method":"CHRONOLOGICAL_VALIDATION_EMPIRICAL_RESIDUALS_UNCALIBRATED"}


class CalibrationTests(unittest.TestCase):
    def test_duplicate_books_are_one_independent_prediction(self):
        rows=[record(),record(book="DraftKings",p=.99)]
        result=audit(rows)
        self.assertEqual(result["overall"]["sample_size"],1)
        self.assertEqual(result["overall"]["wins"],1)
        self.assertEqual(result["overall"]["average_estimated_probability"],.72)
        self.assertEqual(result["overall"]["calibration_gap"],.28)
        self.assertEqual(result["overall"]["brier_score"],round((1-.72)**2,4))
        self.assertEqual(next(b for b in result["bins"] if b["label"]=="70–80%")["sample_size"],1)

    def test_push_pending_late_and_missing_probability_excluded(self):
        no_prob=record(player="2",p=None)
        push=record(player="3",actual=20.5)
        pending=record(player="4",status="PENDING")
        late=record(player="5",captured="2026-11-13T01:00:00Z")
        result=audit([no_prob,push,pending,late])
        self.assertEqual(result["overall"]["sample_size"],0)
        self.assertIsNone(result["overall"]["observed_hit_rate"])

    def test_model_probability_side_is_not_combined_lean(self):
        r=record(original=19,actual=18,line=20.5,p=.68)
        r["original_probability_side"]="UNDER"
        r["side"]="OVER" # combined model chose a different direction
        result=audit([r])
        self.assertEqual(result["overall"]["wins"],1)
        self.assertEqual(result["overall"]["average_estimated_probability"],.68)

    def test_legacy_probability_is_never_backfilled(self):
        r=record()
        r.pop("original_probability_estimate")
        r["experimental_estimate"]=.95
        result=audit([r])
        self.assertEqual(result["overall"]["sample_size"],0)

    def test_invalid_or_mismatched_source_never_calibrates(self):
        r=record(p=1.2)
        other=record(player="2")
        other["original_probability_side"]="UNDER"
        result=audit([r,other])
        self.assertEqual(result["overall"]["sample_size"],0)

    def test_separate_markets_and_error_rates(self):
        rows=[record(player="1",p=.7,actual=24),
              record(player="2",p=.6,actual=15),
              record(player="3",p=.8,actual=23,market="REB")]
        result=audit(rows)
        self.assertEqual(result["overall"]["wins"],2)
        self.assertEqual(result["overall"]["losses"],1)
        self.assertEqual(result["by_stat"]["PTS"]["sample_size"],2)
        self.assertEqual(result["by_stat"]["REB"]["sample_size"],1)
        self.assertFalse(result["sufficient_overall_sample"])
        self.assertTrue(result["no_live_calibration_applied"])


if __name__=="__main__":unittest.main()

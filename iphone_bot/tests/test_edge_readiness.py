import unittest
from datetime import datetime, timezone
from iphone_bot.edge_readiness import evaluate_edge,break_even

NOW=datetime(2026,11,8,17,0,tzinfo=timezone.utc)
CAL={"model":"combined","verified":True,"independent_outcomes":500,
     "distinct_event_dates":16,"chronological_holdout":True,
     "frozen_pregame_predictions":True}
QUOTE={"side":"OVER","line":25.5,"odds":-110,"updated_at":"2026-11-08T16:50:00+00:00"}

def audit(**kw):
    values={"model_probability":0.64,"lower_probability":0.60,
      "calibration":CAL,"quote":QUOTE,"side":"OVER","line":25.5,"now":NOW}
    values.update(kw)
    return evaluate_edge(**values)

class EdgeReadinessTests(unittest.TestCase):
    def test_break_even_and_supported_example(self):
        self.assertAlmostEqual(break_even(-110),110/210)
        record=audit()
        self.assertTrue(record["verified_edge"])
        self.assertEqual(record["status"],"EDGE_READY_FOR_REVIEW")
        self.assertGreater(record["conservative_ev_per_unit"],0)
    def test_current_uncalibrated_sim_never_passes(self):
        record=audit(calibration={"model":"combined","verified":False,
            "independent_outcomes":592,"distinct_event_dates":2})
        self.assertFalse(record["verified_edge"])
        self.assertIn("COMBINED_PROBABILITY_NOT_VALIDATED",record["reasons"])
    def test_prizepicks_requires_complete_slip_payout_model(self):
        self.assertFalse(audit(wager_type="prizepicks")["verified_edge"])
    def test_missing_price_or_wrong_line_never_pass(self):
        self.assertFalse(audit(quote=None)["verified_edge"])
        self.assertFalse(audit(line=26.5)["verified_edge"])
    def test_stale_price_never_passes(self):
        self.assertFalse(audit(quote={**QUOTE,"updated_at":"2026-11-08T15:00:00Z"})["verified_edge"])
    def test_not_enough_conservative_advantage(self):
        record=audit(lower_probability=0.53)
        self.assertEqual(record["status"],"NO_VERIFIED_EDGE")
        self.assertIn("CONSERVATIVE_PROBABILITY_DOES_NOT_CLEAR_PRICE",record["reasons"])
    def test_fabricated_confidence_bound_rejected(self):
        self.assertFalse(audit(lower_probability=0.7)["verified_edge"])

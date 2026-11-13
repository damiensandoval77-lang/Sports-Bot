import unittest
from datetime import datetime, timezone
from iphone_bot.preliminary_edge import preliminary_probability,preliminary_edge

NOW=datetime(2026,11,8,15,0,tzinfo=timezone.utc)
AUDIT={"original_model_only":True,"by_stat":{
 "PTS":{"sample_size":89,"distinct_event_dates":2,
        "observed_hit_rate":.4607,"average_estimated_probability":.6147},
 "REB":{"sample_size":86,"distinct_event_dates":2,
        "observed_hit_rate":.3605,"average_estimated_probability":.613},
 "AST":{"sample_size":71,"distinct_event_dates":2,
        "observed_hit_rate":.5634,"average_estimated_probability":.6691},
 "PRA":{"sample_size":72,"distinct_event_dates":2,
        "observed_hit_rate":.4444,"average_estimated_probability":.6165}}}
PAPER={"generated_at":"2026-11-08T09:52:00+00:00",
       "probability_audit":AUDIT,
       "pipeline_health":{"latest_completed_player_game_date":"2026-11-07"}}
ROW={"start":"2026-11-09T00:00:00+00:00",
     "combined_direction":"Over", "stat":"PTS","line":23.5,
     "reliability_screen":{"status":"MODEL_LEAN"},
     "combined_simulation":{"simulation_count":20000,"calibrated":False,
                            "selected_hit_rate":.72,"push_rate":0},
     "book_quotes":[{"name":"Test Book","line":23.5,"over":-110,
                     "under":-110,"updated_at":"2026-11-08T14:50:00+00:00"}]}

class EarlySampleEdgeTests(unittest.TestCase):
 def test_uses_small_grade_sample_without_claiming_validation(self):
    p=preliminary_probability(.72,"PTS",AUDIT)
    self.assertEqual(p["sample_size"],89)
    self.assertEqual(p["distinct_event_dates"],2)
    self.assertLess(p["probability"],.72)
    self.assertGreater(p["probability"],.60)
    self.assertFalse(p["validated"])
 def test_price_comparison_is_provisional_only(self):
    result=preliminary_edge(ROW,PAPER,now=NOW)
    self.assertEqual(result["status"],"PROVISIONAL_POSITIVE_EV")
    self.assertGreater(result["net_ev_pct"],0)
    self.assertFalse(result["verified_edge"])
    self.assertEqual(result["quote"]["side"],"OVER")
 def test_prizepicks_not_treated_as_sportsbook(self):
    result=preliminary_edge(ROW,PAPER,now=NOW,prizepicks=True)
    self.assertEqual(result["status"],"PRIZEPICKS_SLIP_PAYOUT_REQUIRED")
    self.assertIsNone(result["net_ev_pct"])
 def test_stale_or_different_line_not_claimed(self):
    for quote in (
        {**ROW["book_quotes"][0],"updated_at":"2026-11-08T11:00:00+00:00"},
        {**ROW["book_quotes"][0],"line":24.5}
    ):
        with self.subTest(quote=quote):
            result=preliminary_edge({**ROW,"book_quotes":[quote]},PAPER,now=NOW)
            self.assertEqual(result["status"],"PRELIMINARY_PROBABILITY_ONLY")
            self.assertFalse(result["verified_edge"])
 def test_grades_from_future_not_used(self):
    result=preliminary_edge(ROW,{**PAPER,"generated_at":"2026-11-09T02:00:00+00:00"},now=NOW)
    self.assertEqual(result["status"],"INSUFFICIENT_PRELIMINARY_DATA")
 def test_same_day_game_not_leaked(self):
    result=preliminary_edge(ROW,{**PAPER,"pipeline_health":{"latest_completed_player_game_date":"2026-11-09"}},now=NOW)
    self.assertEqual(result["status"],"INSUFFICIENT_PRELIMINARY_DATA")
 def test_structural_pass_not_promoted_to_positive_ev(self):
    result=preliminary_edge({**ROW,"reliability_screen":{"status":"PASS"}},PAPER,now=NOW)
    self.assertEqual(result["status"],"PASS_STRUCTURAL_SCREEN")
 def test_missing_stat_audit_avoids_estimate(self):
    self.assertIsNone(preliminary_probability(.7,"BLK",AUDIT))

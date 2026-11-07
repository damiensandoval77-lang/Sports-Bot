import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from iphone_bot.assist_v2_shadow_capture import capture,summary,grade

class ShadowCaptureTests(unittest.TestCase):
    def test_reject_stale_board(self):
        board={"status":"EXPERIMENTAL_NON_CALIBRATED","verified_current_matchups":True,
               "generated_at":"2026-11-01T12:00:00+00:00","comparisons":[]}
        with self.assertRaises(ValueError):
            capture(board,[],[],now="2026-11-02T12:00:00+00:00")

    def test_preserve_existing(self):
        board={"status":"EXPERIMENTAL_NON_CALIBRATED","verified_current_matchups":True,
               "generated_at":"2026-11-07T12:00:00+00:00","comparisons":[]}
        old=[{"event_start":"2026-11-06T20:00:00+00:00","player_id":"1","team":"BOS","bookmaker":"x","line":3.5}]
        self.assertEqual(capture(board,[],old,now="2026-11-07T12:01:00+00:00"),old)

    def test_paired_prospective_summary_deduplicates_bookmakers(self):
        row={"event_start":"2026-11-07T20:00:00+00:00",
             "captured_at":"2026-11-07T18:00:00+00:00",
             "player_id":"1","team":"BOS","market":"AST","line":5.5,
             "status":"SETTLED","result":"WIN","actual":7,
             "baseline_projection":4.8,"v2_projection":6.2}
        r=summary([row,{**row,"bookmaker":"second"}])
        self.assertEqual(r["captured"],2)
        self.assertEqual(r["independent_settled_markets"],1)
        self.assertEqual(r["wins"],1)
        self.assertEqual(r["baseline_losses"],1)
        self.assertEqual(r["hit_rate"],1.)
        self.assertEqual(r["baseline_hit_rate"],0.)

    def test_empty_grade_and_summary_are_safe(self):
        self.assertEqual(grade([],[],now="2026-11-07T20:00:00+00:00"),[])
        self.assertIsNone(summary([])["hit_rate"])
        self.assertEqual(summary([])["pending"],0)

    def test_capture_and_verified_final_grade_without_future_data(self):
        board={"status":"EXPERIMENTAL_NON_CALIBRATED","verified_current_matchups":True,
               "generated_at":"2026-11-07T18:00:00+00:00",
               "comparisons":[{"stat":"AST","start":"2026-11-07T21:00:00+00:00",
                               "player_id":"1","player":"Test Player","team":"BOS",
                               "game":"Boston Celtics @ Miami Heat","combined_projection":5.3,
                               "book_quotes":[{"name":"test-book","line":4.5,
                                               "over":-110,"under":-110}]}]}
        prediction={"status":"RESEARCH_FORECAST","projection":6.2,
                    "over_probability":0.68,"push_probability":0.,
                    "latest_prior_date":"2026-11-06","simulations":20000}
        with patch("iphone_bot.assist_v2_shadow_capture.histories",return_value={}), \\
             patch("iphone_bot.assist_v2_shadow_capture.opportunity",return_value={"expected_minutes":30}), \\
             patch("iphone_bot.assist_v2_shadow_capture.forecast",return_value=prediction):
            rows=capture(board,[],[],now="2026-11-07T18:10:00+00:00")
            repeated=capture(board,[],rows,now="2026-11-07T18:11:00+00:00")
        self.assertEqual(len(rows),1)
        self.assertEqual(len(repeated),1)
        self.assertEqual(rows[0]["side"],"OVER")
        self.assertFalse(rows[0]["production_applied"])
        final={"player":"Test Player","date":"2026-11-07","team":"BOS","opponent":"MIA",
               "source":"ESPN_FINAL","final_confirmed":True,"MIN":31,
               "PTS":18,"REB":4,"AST":7}
        graded=grade(rows,[final],now="2026-11-08T01:00:00+00:00")
        self.assertEqual(graded[0]["status"],"SETTLED")
        self.assertEqual(graded[0]["result"],"WIN")
        self.assertEqual(graded[0]["actual"],7)
        self.assertEqual(summary(graded)["independent_settled_markets"],1)

if __name__=="__main__":
    unittest.main()

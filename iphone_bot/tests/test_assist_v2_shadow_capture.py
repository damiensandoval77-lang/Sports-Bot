import unittest
from datetime import datetime,timezone
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

if __name__=="__main__":
    unittest.main()

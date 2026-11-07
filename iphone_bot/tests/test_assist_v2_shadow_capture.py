import unittest
from datetime import datetime,timezone
from iphone_bot.assist_v2_shadow_capture import capture

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

if __name__=="__main__":
    unittest.main()

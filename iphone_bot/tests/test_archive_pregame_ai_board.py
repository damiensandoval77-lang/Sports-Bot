import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.archive_pregame_ai_board import choose

NOW=datetime(2026,11,8,0,15,tzinfo=timezone.utc)
EVENT="2026-11-08T01:00:00Z"

def board(created="2026-11-07T21:15:00Z",n=2,event=EVENT):
    return {"status":"EXPERIMENTAL_NON_CALIBRATED","verified_current_matchups":True,
      "generated_at":created,"comparisons":[{
          "player_id":str(i),"game":"Denver Nuggets @ Indiana Pacers",
          "player":"Test Player","stat":"PTS","start":event,
          "book_quotes":[{"name":"FanDuel","line":25.5,"over":-110,"under":-110}],
          "combined_projection":24.5} for i in range(n)]}

class PregameArchiveTests(unittest.TestCase):
    def test_recover_nonempty_same_day_and_preserve_real_frozen_values(self):
        a=choose([board(n=0),board()],NOW)
        self.assertEqual(a["comparison_rows"],2)
        self.assertEqual(a["games_with_archived_predictions"],1)
        self.assertEqual(a["comparisons"][0]["combined_projection"],24.5)
        self.assertFalse(a["is_live"])
        self.assertFalse(a["live_sportsbook_lines"])
        self.assertFalse(a["probabilities_calibrated"])

    def test_prior_morning_predictions_do_not_count_for_new_date(self):
        self.assertIsNone(choose([board(event="2026-11-07T01:00:00Z")],NOW))

    def test_after_tip_model_predictions_cannot_be_archived(self):
        self.assertIsNone(choose([board(created="2026-11-08T02:00:00Z")],
                                   datetime(2026,11,8,4,0,tzinfo=timezone.utc)))

    def test_reject_unverified_or_no_real_book_prices(self):
        bad=board()
        bad["verified_current_matchups"]=False
        self.assertIsNone(choose([bad],NOW))
        bad=board()
        bad["comparisons"][0]["book_quotes"]=[]
        bad["comparisons"][1]["book_quotes"]=[]
        self.assertIsNone(choose([bad],NOW))

    def test_newer_valid_version_wins_not_empty_revision(self):
        a=choose([board(created="2026-11-07T19:00:00Z"),
                  board(created="2026-11-07T22:00:00Z"),
                  board(created="2026-11-07T23:00:00Z",n=0)],NOW)
        self.assertEqual(a["original_board_generated_at"],"2026-11-07T22:00:00+00:00")

if __name__=="__main__":unittest.main()

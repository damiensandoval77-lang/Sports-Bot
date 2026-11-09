import unittest
from datetime import datetime, timedelta, timezone
from iphone_bot.publish_prizepicks_site import summarize

class PrizePicksHealthPublication(unittest.TestCase):
    def test_unassigned_reasons_are_published(self):
        start=(datetime.now(timezone.utc)+timedelta(hours=6)).isoformat()
        board={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
               "generated_at":datetime.now(timezone.utc).isoformat(),
               "provider_status":"fresh","unassigned_or_ambiguous_events":5,
               "unassigned_reason_counts":{"team_not_in_future_schedule":3,
                                           "tipoff_time_mismatch":2},
               "board_offers":[{"id":"a","player":"Example","team":"BOS",
                                "game":"Boston Celtics @ Milwaukee Bucks",
                                "stat":"PTS","line":20.5,"starts_at":start,
                                "observed_at":datetime.now(timezone.utc).isoformat(),
                                "more_tier":"standard","source":"independent_prizepicksapi_com",
                                "is_demo":False}],"offers":[]}
        schedule={"games":[{"game":"Boston Celtics @ Milwaukee Bucks","start":start}],
                  "coverage_complete":True}
        _, report=summarize(board,schedule)
        self.assertTrue(report["source_unassigned_reasons_available"])
        self.assertEqual(report["source_unassigned_reason_counts"],
                         board["unassigned_reason_counts"])
        self.assertEqual(report["known_upcoming_games_with_lines"],1)

    def test_old_source_does_not_fake_new_diagnostic_proof(self):
        board={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
               "board_offers":[],"offers":[],"unassigned_or_ambiguous_events":5}
        _, report=summarize(board,{"games":[]})
        self.assertFalse(report["source_unassigned_reasons_available"])
        self.assertEqual(report["source_unassigned_reason_counts"],{})

if __name__=="__main__":unittest.main()

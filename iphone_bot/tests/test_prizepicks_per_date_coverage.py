import unittest
from datetime import datetime, timedelta, timezone
from iphone_bot.publish_prizepicks_site import summarize

class DailyCoverageTests(unittest.TestCase):
    def test_partial_board_does_not_claim_no_lines(self):
        now=datetime.now(timezone.utc)
        today=(now+timedelta(hours=5)).isoformat()
        later=(now+timedelta(hours=30)).isoformat()
        a="Boston Celtics @ Milwaukee Bucks"
        b="Miami Heat @ Utah Jazz"
        source={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
                "partial_board":True,"complete_provider_board":False,
                "board_offers":[{"source":"independent_prizepicksapi_com",
                                 "is_demo":False,"game":a,"starts_at":today,
                                 "more_tier":"standard"}],"offers":[]}
        schedule={"games":[{"game":a,"start":today},
                           {"game":b,"start":later}]}
        _,h=summarize(source,schedule)
        by={g["game"]:g for g in h["per_game_coverage"]}
        self.assertEqual(by[a]["coverage_status"],"LINES_OBSERVED")
        self.assertEqual(by[b]["coverage_status"],"NOT_OBSERVED_IN_PARTIAL_FEED")
        self.assertFalse(h["missing_lines_are_provider_absence_verified"])
        self.assertEqual(sum(x["games_without_lines"] for x in
                             h["coverage_by_eastern_date"].values()),1)

    def test_consecutive_night_identical_matchups_have_independent_coverage(self):
        now=datetime.now(timezone.utc)
        first=(now+timedelta(hours=6)).isoformat()
        second=(now+timedelta(hours=29)).isoformat()
        same="Oklahoma City Thunder @ Portland Trail Blazers"
        source={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
                "partial_board":True,"complete_provider_board":False,
                "board_offers":[{"source":"independent_prizepicksapi_com",
                                 "is_demo":False,"game":same,"starts_at":first,
                                 "more_tier":"standard"}],"offers":[]}
        schedule={"games":[{"game":same,"start":first},
                           {"game":same,"start":second}]}
        _,health=summarize(source,schedule)
        self.assertEqual(health["known_upcoming_scheduled_games"],2)
        self.assertEqual(health["known_upcoming_games_with_lines"],1)
        self.assertEqual(len(health["per_game_coverage"]),2)
        self.assertEqual(health["per_game_coverage"][0]["line_offer_count"],1)
        self.assertEqual(health["per_game_coverage"][1]["line_offer_count"],0)
        self.assertEqual(health["per_game_coverage"][1]["coverage_status"],"NOT_OBSERVED_IN_PARTIAL_FEED")
        self.assertEqual(len(health["known_upcoming_games_without_lines"]),1)

    def test_complete_board_missing_is_explicit(self):
        start=(datetime.now(timezone.utc)+timedelta(hours=5)).isoformat()
        _,h=summarize({"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
                       "partial_board":False,"complete_provider_board":True,
                       "board_offers":[],"offers":[]},
                      {"games":[{"game":"Miami Heat @ Utah Jazz","start":start}]})
        self.assertEqual(h["per_game_coverage"][0]["coverage_status"],
                         "NOT_OBSERVED_IN_COMPLETE_FEED")
        self.assertTrue(h["missing_lines_are_provider_absence_verified"])

if __name__=="__main__":unittest.main()

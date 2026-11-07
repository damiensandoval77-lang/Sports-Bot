"""Final-boxscore eligibility and verified completion regression tests."""
import unittest
from datetime import datetime,timezone
from iphone_bot.fetch_final_boxscores import (
    pending_games,box_player,espn_final_events,minutes,gather)

def pick(start="2026-11-06T00:00:00Z",status="PENDING"):
    return {"event_start":start,"game":"Boston Celtics @ Charlotte Hornets",
            "status":status,"player_id":"10","team":"BOS"}


class FinalBoxscoreSettlementTests(unittest.TestCase):
    def test_actual_pending_game_enters_grading_window(self):
        now=datetime(2026,11,7,6,tzinfo=timezone.utc)
        games=pending_games([pick()],now)
        self.assertEqual(games,{("2026-11-05","BOS","CHA")})
        self.assertEqual(pending_games([pick(status="SETTLED")],now),set())

    def test_not_yet_finished_games_are_not_eligible(self):
        now=datetime(2026,11,7,2,tzinfo=timezone.utc)
        self.assertEqual(pending_games([pick("2026-11-07T01:30:00Z")],now),set())

    def test_espn_requires_completed_event_status(self):
        fixture={"events":[{"id":"1","date":"2026-11-07T00:00:00Z",
                  "status":{"type":{"completed":False}},
                  "competitions":[{"competitors":[
                    {"homeAway":"away","team":{"abbreviation":"BOS"}},
                    {"homeAway":"home","team":{"abbreviation":"CHA"}}]}]}]}
        self.assertEqual(espn_final_events(fixture),[])
        fixture["events"][0]["status"]["type"]["completed"]=True
        self.assertEqual(len(espn_final_events(fixture)),1)

    def test_minutes_and_exact_final_player_boxscore(self):
        self.assertAlmostEqual(minutes("PT32M30S"),32.5)
        valid=box_player("Real Player","BOS","CHA","2026-11-06",
            24,8,7,"30:00","ESPN_FINAL","123")
        self.assertTrue(valid["final_confirmed"])
        self.assertEqual(valid["PRA"],39)
        self.assertIsNone(box_player("Real Player","BOS","BOS",
            "2026-11-06",24,8,7,30,"ESPN_FINAL","123"))
        self.assertIsNone(box_player("Real Player","BOS","CHA",
            "2026-11-06",24,8,7,None,"ESPN_FINAL","123"))

    def test_no_pending_matches_never_calls_provider(self):
        def blocked(_):
            raise AssertionError("Provider should not be queried for empty pending matchups")
        found,status=gather([],request=blocked)
        self.assertEqual(found,[])
        self.assertEqual(status["status"],"NO_ELIGIBLE_PENDING_MATCHUPS")

if __name__=="__main__":unittest.main()

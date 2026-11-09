import datetime as dt
import unittest
from iphone_bot.board_readiness_audit import inspect

NOW = dt.datetime(2026, 11, 9, 12, tzinfo=dt.timezone.utc)

def fixtures():
    odds={"updated_at":NOW.isoformat(), "slate_events_available":2,
          "slate_events_checked":2, "disclaimer":"Sportsbook lines"}
    board={"generated_at":NOW.isoformat(),"status":"ACTIVE","fresh_pregame_board":True,
           "fresh_board_games":["game-a","game-b"]}
    paper={"generated_at":NOW.isoformat(),"captured":8,"settled":5,"pending":2,"void_dnp":1}
    return odds,board,paper

class BoardReadinessTests(unittest.TestCase):
    def test_complete_fresh_snapshot_passes(self):
        self.assertTrue(inspect(*fixtures(),now=NOW)["ready"])

    def test_research_timestamp_is_not_pregame_board(self):
        odds,board,paper=fixtures()
        board["status"]="RESEARCH_AUDIT_ONLY_NO_FRESH_PREGAME_BOARD"
        del board["fresh_pregame_board"]
        self.assertFalse(inspect(odds,board,paper,now=NOW)["ready"])

    def test_missing_matchup_coverage_fails(self):
        odds,board,paper=fixtures()
        odds["slate_events_checked"]=0
        result=inspect(odds,board,paper,now=NOW)
        self.assertFalse(result["ready"])
        self.assertFalse(next(c for c in result["checks"] if c["code"]=="GAME_COVERAGE")["passed"])

    def test_stale_odds_fails(self):
        odds,board,paper=fixtures()
        odds["updated_at"]=(NOW-dt.timedelta(hours=4)).isoformat()
        self.assertFalse(inspect(odds,board,paper,now=NOW)["ready"])

    def test_inconsistent_grading_totals_fails(self):
        odds,board,paper=fixtures()
        paper["settled"]=4
        self.assertFalse(inspect(odds,board,paper,now=NOW)["ready"])

    def test_no_games_is_not_automatically_a_failure(self):
        odds,board,paper=fixtures()
        odds["slate_events_available"]=0
        odds["slate_events_checked"]=0
        self.assertTrue(inspect(odds,board,paper,now=NOW)["ready"])

if __name__=="__main__":
    unittest.main()

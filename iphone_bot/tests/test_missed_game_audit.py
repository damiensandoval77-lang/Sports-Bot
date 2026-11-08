import unittest
from iphone_bot.missed_game_audit import inspect

def record(date="2026-11-07T00:00:00Z",game="Boston Celtics @ Charlotte Hornets",status="PENDING"):
    return {"event_start":date,"captured_at":"2026-11-06T22:00:00Z",
      "game":game,"market":"PTS","player_id":"9","team":"BOS",
      "status":status}

class MissedGames(unittest.TestCase):
    def test_celtics_saved_game_is_reported_not_fabricated(self):
        rows=[record()]
        report=inspect(rows,now="2026-11-07T06:00:00Z")
        self.assertEqual(report["unique_matchups_with_captures"],1)
        self.assertEqual(report["earliest_saved_game_date"],"2026-11-06")
        self.assertEqual(report["celtics_matchups"][0]["pregame_captures"],1)
        self.assertEqual(report["celtics_matchups"][0]["diagnosis"],
                         "WAITING_FOR_VERIFIED_COMPLETED_PLAYER_BOXSCORES")
        self.assertEqual(report["total_saved_bookmaker_captures"],1)
    def test_reports_stored_outcomes(self):
        x=record(status="SETTLED")
        report=inspect([x],now="2026-11-07T06:00:00Z")
        self.assertEqual(report["matchups"][0]["settled"],1)
        self.assertEqual(report["matchups"][0]["diagnosis"],"FULLY_SETTLED_VERIFIED_GAME")
    def test_partial_game_is_not_marked_fully_settled(self):
        completed=record(status="SETTLED")
        pending=record()
        pending["player_id"]="10"
        result=inspect([completed,pending],now="2026-11-07T06:00:00Z")
        match=result["matchups"][0]
        self.assertEqual(match["settled"],1)
        self.assertEqual(match["pending"],1)
        self.assertEqual(match["pending_unique_players"],1)
        self.assertEqual(match["diagnosis"],
                         "PARTIALLY_SETTLED_MISSING_PLAYER_BOXES_OR_DNP")

    def test_nightly_accuracy_ignores_alternate_quotes(self):
        winner=record(status="SETTLED")
        winner.update({"result":"WIN","captured_at":"2026-11-06T22:00:00Z"})
        alternate=dict(winner,bookmaker="Other",line=25.5,
                       result="LOSS",captured_at="2026-11-06T22:05:00Z")
        loser=record(status="SETTLED")
        loser.update({"player_id":"10","result":"LOSS"})
        outstanding=record()
        outstanding["player_id"]="11"
        night=inspect([winner,alternate,loser,outstanding],
                      now="2026-11-07T06:00:00Z")["nightly_grading"][0]
        self.assertEqual(night["captured_independent_markets"],3)
        self.assertEqual(night["graded_independent_markets"],2)
        self.assertEqual(night["pending_independent_markets"],1)
        self.assertEqual((night["wins"],night["losses"]),(1,1))
        self.assertEqual(night["hit_rate_ex_push"],0.5)

    def test_empty_ledger_has_no_fake_historical_games(self):
        report=inspect([],now="2026-11-07T06:00:00Z")
        self.assertEqual(report["celtics_matchups"],[])
        self.assertIsNone(report["earliest_saved_game_date"])

if __name__=="__main__":unittest.main()

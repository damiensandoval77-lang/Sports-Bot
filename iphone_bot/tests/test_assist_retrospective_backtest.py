import unittest
from iphone_bot.assist_retrospective_backtest import evaluation

def games(n=10):
    return [{"id":"10","team":"BOS","date":f"2026-10-{10+i:02d}",
      "MIN":30,"PTS":20,"REB":6,"AST":4,"FGA":15} for i in range(n)]
def pick(player="10",time="2026-11-07T01:00:00Z",at="2026-11-06T21:00:00Z",line=4.5):
    return {"status":"SETTLED","player_id":player,"player":"Test Player",
      "team":"BOS","game":"Boston Celtics @ New York Knicks",
      "market":"AST","event_start":time,"captured_at":at,
      "original_projection":6,"opponent_shadow_projection":6,
      "line":line,"actual":4,"bookmaker":"FanDuel"}

class AssistRetrospectiveTests(unittest.TestCase):
    def test_exact_frozen_same_market_pair(self):
        a=evaluation([pick()],games())
        self.assertEqual(a["overall"]["matched_assist_markets"],1)
        self.assertEqual(a["overall"]["combined_ai"]["wins"],0)
        self.assertEqual(a["overall"]["assist_shadow_v1"]["wins"],0)
        self.assertLess(a["overall"]["assist_shadow_mae"],a["overall"]["combined_ai_mae"])
        self.assertTrue(a["not_pregame_locked_shadow_predictions"])
    def test_new_game_row_not_used_as_prior(self):
        a=evaluation([pick()],games())
        future={"id":"10","team":"BOS","date":"2026-11-06",
            "MIN":58,"PTS":78,"REB":22,"AST":30,"FGA":36}
        b=evaluation([pick()],games()+[future])
        self.assertEqual(a["overall"],b["overall"])
    def test_duplicate_quotes_not_counted_twice(self):
        q=pick()
        alt={**q,"bookmaker":"DraftKings","captured_at":"2026-11-06T22:00:00Z"}
        a=evaluation([q,alt],games())
        self.assertEqual(a["overall"]["matched_assist_markets"],1)
    def test_no_fake_backtest_if_no_prior_history(self):
        a=evaluation([pick()],[])
        self.assertEqual(a["overall"]["matched_assist_markets"],0)
        self.assertEqual(a["eligible_assist_markets_saved"],1)
        self.assertFalse(a["production_ai_unchanged"] is False)

if __name__=="__main__":unittest.main()

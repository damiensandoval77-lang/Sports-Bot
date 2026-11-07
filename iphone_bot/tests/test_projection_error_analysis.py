import unittest
from iphone_bot.projection_error_analysis import report

def row(player="1",stat="PTS",actual=25,status="SETTLED"):
    return {"status":status,"event_start":"2026-11-07T00:10:00Z",
       "captured_at":"2026-11-06T21:00:00Z",
       "player_id":player,"player":"Test "+player,"team":"BOS",
       "game":"Boston Celtics @ Charlotte Hornets",
       "market":stat,"line":20.5,"actual":actual,
       "bookmaker":"FanDuel","original_projection":21.,
       "opponent_shadow_projection":23.,"combined_projection":22.,
       "settlement_source":"CBS_FINAL_VERIFIED"}

class ErrorAnalysisTests(unittest.TestCase):
    def test_separate_markets_and_models_no_duplicate_books(self):
        a=row()
        duplicate={**a,"bookmaker":"DraftKings","captured_at":"2026-11-06T22:00:00Z","line":22.5}
        b=row("2","REB",12)
        result=report([a,duplicate,b])
        self.assertEqual(result["sample_independent_combined_markets"],2)
        self.assertEqual(result["combined_by_market"]["PTS"]["markets"],1)
        self.assertEqual(result["combined_by_market"]["REB"]["markets"],1)
        self.assertEqual(result["combined"]["over_projected"],1)
        self.assertEqual(result["combined"]["under_projected"],1)
        self.assertEqual(result["combined_by_market"]["PTS"]["mae"],3)
        self.assertFalse(result["combined"]["direction_hit_rate"] is None)
    def test_pending_never_in_metrics(self):
        r=report([row(status="PENDING")])
        self.assertEqual(r["sample_independent_combined_markets"],0)
        self.assertIsNone(r["combined"]["mae"])
    def test_only_locked_earliest_and_no_mutation(self):
        early=row()
        late={**early,"bookmaker":"DraftKings","captured_at":"2026-11-07T02:00:00Z"}
        original=dict(early)
        r=report([late,early])
        self.assertEqual(r["sample_independent_combined_markets"],1)
        self.assertEqual(early,original)
    def test_market_misses_ranked_by_absolute_error(self):
        r=report([row("2",actual=11),row("1",actual=20)])
        biggest=r["largest_combined_misses_by_market"]["PTS"]
        self.assertEqual(biggest[0]["player_id"],"2")
        self.assertEqual(biggest[0]["error"],11)

if __name__=="__main__":unittest.main()

import unittest
from iphone_bot.settlement_merge import merge
from iphone_bot.paper_pick_pipeline import identity

def pending(player="123"):
    return {"event_start":"2026-11-07T00:00:00Z",
        "captured_at":"2026-11-06T22:00:00Z",
        "player_id":player,"player":"Test Player","team":"BOS",
        "game":"Boston Celtics @ Charlotte Hornets",
        "market":"PTS","bookmaker":"DraftKings",
        "line":20.5,"side":"OVER","american_odds":-110,
        "original_projection":23.,"combined_projection":24.,
        "status":"PENDING"}
class SafeMerge(unittest.TestCase):
    def test_merge_results_preserves_original_capture_and_newer_picks(self):
        original=pending()
        another=pending("999")
        settled={**original,"status":"SETTLED","actual":25.,
                 "result":"WIN","paper_profit_units":.90909,
                 "settled_at":"2026-11-07T07:00:00Z",
                 "settlement_source":"ESPN_FINAL",
                 "original_projection":999.,
                 "captured_at":"2026-11-06T22:00:00Z"}
        out=merge([original,another],[settled])
        self.assertEqual(len(out),2)
        updated=[r for r in out if r["player_id"]=="123"][0]
        self.assertEqual(updated["status"],"SETTLED")
        self.assertEqual(updated["actual"],25.)
        self.assertEqual(updated["original_projection"],23.)
        self.assertEqual(updated["combined_projection"],24.)
        self.assertEqual(updated["captured_at"],original["captured_at"])
        self.assertEqual([r for r in out if r["player_id"]=="999"][0]["status"],"PENDING")
    def test_no_downgrade_existing_settled(self):
        record={**pending(),"status":"SETTLED","actual":22.,
                "result":"WIN","paper_profit_units":.9}
        out=merge([record],[pending()])
        self.assertEqual(out[0]["actual"],22.)
        self.assertEqual(out[0]["status"],"SETTLED")
    def test_idempotent(self):
        initial=[pending()]
        merged=merge(initial,initial)
        self.assertEqual(merge(merged,merged),merged)
        self.assertEqual(len({identity(r) for r in merged}),len(merged))

if __name__=="__main__":unittest.main()

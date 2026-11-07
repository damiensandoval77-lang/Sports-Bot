import unittest
from iphone_bot.selection_quality_audit import analyze,wilson_lower

def record(player="10",market="AST",actual=7,status="SETTLED",
           start="2026-11-07T00:10:00Z",line=5.5,projection=6.5):
    return {"player_id":player,"player":"Test "+player,"game":"Boston Celtics @ Charlotte Hornets",
        "team":"BOS","market":market,"status":status,
        "event_start":start,"captured_at":"2026-11-06T21:00:00Z",
        "bookmaker":"FanDuel","actual":actual,"line":line,
        "original_projection":projection-1,
        "opponent_shadow_projection":projection+1,
        "combined_projection":projection}

class SelectionQualityTests(unittest.TestCase):
    def test_pregame_dedupe_and_fixed_market_edge_bands(self):
        a=record()
        b={**a,"bookmaker":"DraftKings","captured_at":"2026-11-06T22:00:00Z","line":3.5}
        c=record("11","PTS",actual=11,projection=12,line=14)
        result=analyze([a,b,c])
        self.assertEqual(result["overall"]["independent_markets"],2)
        self.assertEqual(result["by_market"]["AST"]["edge_bands"][1]["independent_markets"],1)
        self.assertEqual(result["by_market"]["PTS"]["edge_bands"][2]["independent_markets"],1)
        self.assertFalse(result["overall"]["sample_threshold_met"])
        self.assertEqual(result["recommended_real_money_plays"],0)
    def test_no_lookahead_from_unsettled_and_late(self):
        pending=record(status="PENDING")
        late=record(player="11")
        late["captured_at"]="2026-11-07T01:00:00Z"
        self.assertEqual(analyze([pending,late])["overall"]["independent_markets"],0)
    def test_push_and_no_lean_not_hit(self):
        p=record(actual=5.5)
        q=record(player="11",projection=5.5)
        x=analyze([p,q])
        self.assertEqual(x["overall"]["independent_markets"],0)
        self.assertEqual(x["excluded"]["push"],1)
        self.assertEqual(x["excluded"]["no_direction"],1)
    def test_single_date_and_small_sample_cannot_validate(self):
        records=[record(player=str(i)) for i in range(100)]
        x=analyze(records)
        self.assertEqual(x["overall"]["distinct_game_dates"],1)
        self.assertFalse(x["overall"]["sample_threshold_met"])
        self.assertLess(wilson_lower(100,100),1)
        self.assertEqual(x["status"],"RESEARCH_ONLY_NO_VALIDATED_BETTING_EDGE")
    def test_unchanged_production_forecasts(self):
        x=record()
        copy=dict(x)
        result=analyze([x])
        self.assertEqual(x,copy)
        self.assertTrue(result["production_predictions_unchanged"])
        self.assertTrue(result["production_probability_unchanged"])

if __name__=="__main__":unittest.main()

"""Frozen four-market cards never regrade against synthetic markets."""
import unittest
try:
    from iphone_bot.multimarket_forecast_ledger import merge
except ImportError:
    from multimarket_forecast_ledger import merge

def prediction(stat="PRA",p=30.0,capture="2026-11-09T20:00:00Z"):
    return {"player_id":"123","team":"BOS","game":"Boston Celtics @ New York Knicks",
      "start":"2026-11-10T00:00:00Z","stat":stat,"line":31.5,
      "projection":p,"market_updated":"2026-11-09T19:00:00Z",
      "captured_at":capture,"pickem_tier":"standard",
      "standard_line_two_sided_verified":True,"research_only":True,
      "calibrated_probability":None,
      "estimated_hit_chance":{"modeled_direction":"Less"}}

def feed(*values):
    return {"status":"LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED","predictions":list(values)}

class ImmutableMarketsTests(unittest.TestCase):
    def test_first_prediction_kept_when_line_moves(self):
        before=merge({},feed(prediction()),{})
        changed=prediction(p=100.0,capture="2026-11-09T22:00:00Z")
        changed["line"]=35.5
        result=merge(before,feed(changed),{})
        self.assertEqual(len(result["records"]),1)
        self.assertEqual(result["records"][0]["projection"],30.)
        self.assertEqual(result["records"][0]["line"],31.5)

    def test_four_markets_can_grade_independently(self):
        before=merge({},feed(*(prediction(stat) for stat in ("PTS","REB","AST","PRA"))),{})
        finals={"records":[{"status":"GRADED","player_id":"123","team":"BOS",
         "game":"Boston Celtics @ New York Knicks","start":"2026-11-10T00:00:00Z",
         "stat":stat,"actual":28.0,"final_source":"NBA_CDN_FINAL",
         "source_game_id":"0022600999"} for stat in ("PTS","REB","AST","PRA")]}
        out=merge(before,{},finals)
        self.assertEqual(out["new_verified_grades"],4)
        self.assertEqual(sum(v["graded"] for v in out["market_metrics"].values()),4)
        self.assertFalse(out["existing_grades_modified"])

    def test_after_tipoff_cannot_backfill(self):
        p=prediction(capture="2026-11-10T00:01:00Z")
        self.assertEqual(merge({},feed(p),{})["records"],[])

    def test_unknown_box_source_cannot_grade(self):
        initial=merge({},feed(prediction()),{})
        final={"records":[{"status":"GRADED","player_id":"123","team":"BOS",
         "game":"Boston Celtics @ New York Knicks","start":"2026-11-10T00:00:00Z",
         "stat":"PRA","actual":29.0,"final_source":"FAKE",
         "source_game_id":"1"}]}
        self.assertEqual(merge(initial,{},final)["market_metrics"]["PRA"]["graded"],0)

if __name__=="__main__":
    unittest.main()

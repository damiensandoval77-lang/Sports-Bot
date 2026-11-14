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
    def test_first_prediction_preserved_and_new_pretip_threshold_separately_frozen(self):
        before=merge({},feed(prediction()),{})
        changed=prediction(p=100.0,capture="2026-11-09T22:00:00Z")
        changed["line"]=35.5
        result=merge(before,feed(changed),{})
        self.assertEqual(len(result["records"]),2)
        original=next(x for x in result["records"] if x["line"]==31.5)
        moved=next(x for x in result["records"] if x["line"]==35.5)
        self.assertEqual(original["projection"],30.)
        self.assertEqual(moved["projection"],100.)

    def test_multiple_pretip_thresholds_grade_independently_at_original_lines(self):
        first=prediction()
        moved=prediction(p=30.,capture="2026-11-09T22:00:00Z")
        moved["market_updated"]="2026-11-09T21:00:00Z"
        moved["line"]=35.5
        frozen=merge({},feed(first,moved),{})
        final={"records":[{"status":"GRADED","player_id":"123","team":"BOS",
           "game":first["game"],"start":first["start"],"stat":"PRA",
           "actual":33.,"final_source":"NBA_CDN_FINAL","source_game_id":"0022600999"}]}
        result=merge(frozen,{},final)
        self.assertEqual(len(result["records"]),2)
        original=next(x for x in result["records"] if x["line"]==31.5)
        revision=next(x for x in result["records"] if x["line"]==35.5)
        self.assertTrue(original["direction_hit"] is False)
        self.assertTrue(revision["direction_hit"] is True)
        self.assertEqual(original["grade"],"GRADED")
        self.assertEqual(revision["grade"],"GRADED")

    def test_revised_threshold_captured_after_tipoff_never_frozen(self):
        original=prediction()
        changed=prediction(capture="2026-11-10T00:02:00Z")
        changed["line"]=35.5
        result=merge(merge({},feed(original),{}),feed(changed),{})
        self.assertEqual(len(result["records"]),1)

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

    def test_verified_dnp_is_excluded_not_pending_or_loss(self):
        first=prediction()
        later=prediction(capture="2026-11-09T22:00:00Z")
        later["line"]=35.5
        later["market_updated"]="2026-11-09T21:00:00Z"
        saved=merge({},feed(first,later),{})
        dnp={"records":[{"status":"EXCLUDED_VERIFIED_DNP",
            "player_id":"123","team":"BOS","game":first["game"],
            "start":first["start"],"stat":"PRA","actual":None,
            "final_source":"NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
            "verified_dnp_reason":"INACTIVE_CROSSCHECKED",
            "source_game_id":"0022600999"}]}
        settled=merge(saved,{},dnp)
        self.assertEqual(settled["new_verified_dnp_exclusions"],2)
        self.assertEqual(settled["market_metrics"]["PRA"]["pending"],0)
        self.assertEqual(settled["market_metrics"]["PRA"]["graded"],0)
        self.assertEqual(settled["market_metrics"]["PRA"]["verified_dnp_excluded"],2)
        self.assertTrue(all(x["grade"]=="EXCLUDED_VERIFIED_DNP" and
                            x["actual"] is None and x["direction_hit"] is None
                            for x in settled["records"]))
        self.assertEqual(merge(settled,{},dnp)["new_verified_dnp_exclusions"],0)

    def test_explicit_official_final_dnp_settles_each_original_threshold(self):
        for source,event in (("NBA_CDN_FINAL","0022600999"),("ESPN_FINAL","401909298")):
            with self.subTest(source=source):
                first=prediction(); later={**first,"line":35.5}
                saved=merge({},feed(first,later),{})
                row={"status":"EXCLUDED_VERIFIED_DNP","player_id":"123","team":"BOS",
                     "game":first["game"],"start":first["start"],"stat":"PRA",
                     "actual":None,"final_source":source,"source_game_id":event,
                     "verified_dnp_reason":"INACTIVE_INJURY"}
                result=merge(saved,{}, {"records":[row]})
                self.assertEqual(result["new_verified_dnp_exclusions"],2)
                self.assertEqual(result["new_verified_grades"],0)
                self.assertTrue(all(r["actual"] is None and r["direction_hit"] is None
                                    and r["absolute_error"] is None for r in result["records"]))
                self.assertEqual([r["projection"] for r in result["records"]],[30.,30.])
                for change in ({"actual":0},{"verified_dnp_reason":""},{"source_game_id":""}):
                    rejected=merge(saved,{}, {"records":[{**row,**change}]})
                    self.assertEqual(rejected["new_verified_dnp_exclusions"],0)

    def test_unverified_dnp_cannot_change_a_pick(self):
        p=prediction()
        saved=merge({},feed(p),{})
        fake={"records":[{"status":"EXCLUDED_VERIFIED_DNP",
             "player_id":"123","team":"BOS","game":p["game"],
             "start":p["start"],"stat":"PRA",
             "final_source":"UNCONFIRMED","source_game_id":"1",
             "verified_dnp_reason":"claim","actual":None}]}
        out=merge(saved,{},fake)
        self.assertEqual(out["records"][0]["grade"],"PENDING")
        self.assertEqual(out["market_metrics"]["PRA"]["pending"],1)

    def test_verified_dnp_and_scored_final_disagree_so_do_not_settle(self):
        p=prediction()
        saved=merge({},feed(p),{})
        common={"player_id":"123","team":"BOS","game":p["game"],
                "start":p["start"],"stat":"PRA","source_game_id":"0022600999"}
        contradictory={"records":[
             {**common,"status":"EXCLUDED_VERIFIED_DNP","actual":None,
              "final_source":"NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
              "verified_dnp_reason":"INACTIVE"},
             {**common,"status":"GRADED","actual":30,
              "final_source":"NBA_CDN_FINAL"}]}
        out=merge(saved,{},contradictory)
        self.assertEqual(out["records"][0]["grade"],"PENDING")

    def test_grader_not_blocked_behind_model_training(self):
        from pathlib import Path
        path=Path(__file__).resolve().parents[2]/".github/workflows/nba-new-ai-multimarket-grade.yml"
        workflow=path.read_text(encoding="utf-8")
        self.assertIn("group: nba-new-ai-final-settlement",workflow)
        self.assertIn("ref: ${{ github.head_ref || 'main' }}",workflow)
        self.assertIn("python -m iphone_bot.multimarket_forecast_ledger",workflow)
        self.assertIn("python -m iphone_bot.merge_new_ai_publishing",workflow)

    def test_unknown_box_source_cannot_grade(self):
        initial=merge({},feed(prediction()),{})
        final={"records":[{"status":"GRADED","player_id":"123","team":"BOS",
         "game":"Boston Celtics @ New York Knicks","start":"2026-11-10T00:00:00Z",
         "stat":"PRA","actual":29.0,"final_source":"FAKE",
         "source_game_id":"1"}]}
        self.assertEqual(merge(initial,{},final)["market_metrics"]["PRA"]["graded"],0)

if __name__=="__main__":
    unittest.main()

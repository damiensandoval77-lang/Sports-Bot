import unittest
from iphone_bot.paper_pick_pipeline import snapshot,settle
from iphone_bot.settlement_merge import merge
from iphone_bot.extreme_miss_forensics import report

AT="2026-11-12T20:00:00Z"
START="2026-11-13T00:30:00Z"

def market(stat="PTS"):
    return {"player":"Sample Player","player_id":"123","team":"BOS",
      "game":"Boston Celtics @ Miami Heat","start":START,"stat":stat,
      "projection":24.,"combined_projection":25.,
      "model_feature_audit":{"method":"EXACT_INPUT_TO_ORIGINAL_TRAINED_MODEL_PREGAME",
            "features":{"MIN_L5":35,"PTS_L5":24.},"sample_games":10},
      "minutes_research":{"status":"RESEARCH_ESTIMATE_UNVERIFIED_LINEUP",
                          "expected_minutes":34.},
      "minutes_v2_research":{"expected_minutes":33.},
      "injury_status":"AVAILABLE",
      "book_quotes":[{"name":"FanDuel","line":21.5,"over":-110,"under":-110}]}

def game(minutes=19,points=10):
    return {"player":"Sample Player","team":"BOS","opponent":"MIA",
         "date":"2026-11-12","PTS":points,"REB":4,"AST":3,
         "PRA":points+7,"MIN":minutes,"source":"NBA_CDN_FINAL",
         "final_confirmed":True,"source_game_id":"0022600030"}

class ExtremeMissForensicsTests(unittest.TestCase):
    def test_freeze_exact_input_and_compare_verified_minutes_after_settlement(self):
        first=snapshot([market()],AT)
        self.assertEqual(first[0]["model_feature_audit"]["features"]["MIN_L5"],35)
        self.assertEqual(first[0]["frozen_minutes_research"]["expected_minutes"],34)
        final=settle(first,[game()],"2026-11-13T04:00:00Z")
        self.assertEqual(final[0]["actual_minutes"],19)
        safe=merge(first,final)
        self.assertEqual(safe[0]["model_feature_audit"],first[0]["model_feature_audit"])
        self.assertEqual(safe[0]["actual_minutes"],19)
        a=report(safe)
        self.assertEqual(a["by_market"]["PTS"]["extreme"]["markets"],1)
        self.assertEqual(a["by_market"]["PTS"]["extreme_under_minutes_by_at_least_5"],1)
        self.assertFalse(a["causal_explanation_established"])

    def test_no_final_minutes_does_not_fabricate(self):
        p=snapshot([market()],AT)
        self.assertEqual(report(p)["independent_settled_markets"],0)
        legacy=settle(p,[game()],"2026-11-13T04:00:00Z")
        legacy[0].pop("model_feature_audit")
        legacy[0].pop("frozen_minutes_research")
        a=report(legacy)
        self.assertEqual(a["by_market"]["PTS"]["extreme_unexplained_minutes_coverage"],1)
        self.assertEqual(a["data_gaps"]["missing_frozen_pregame_expected_minutes"],1)
        self.assertTrue(a["historical_pregame_feature_backfill_permitted"] is False)

    def test_original_pick_is_immutable_during_forensic_capture(self):
        x=market()
        old=snapshot([x],AT)
        x["model_feature_audit"]["features"]["MIN_L5"]=10
        updated=snapshot([x],"2026-11-12T21:00:00Z",old)
        self.assertEqual(updated[0]["model_feature_audit"]["features"]["MIN_L5"],35)
        self.assertEqual(updated[0]["captured_at"],old[0]["captured_at"])

    def test_duplicate_books_one_independent_market(self):
        p=market()
        p["book_quotes"].append({"name":"DraftKings","line":22.5,"over":-115,"under":-105})
        frozen=snapshot([p],AT)
        finished=settle(frozen,[game()],"2026-11-13T04:00:00Z")
        self.assertEqual(report(finished)["independent_settled_markets"],1)

    def test_legacy_frozen_two_model_midpoint_is_counted_without_postgame_reestimate(self):
        p=market()
        p["shadow_projection"]=26
        finished=settle(snapshot([p],AT),[game()],
                        "2026-11-13T04:00:00Z")
        finished[0].pop("combined_projection")
        observed=report(finished)
        self.assertEqual(observed["independent_settled_markets"],1)
        self.assertEqual(observed["data_gaps"]["legacy_combined_from_frozen_components"],1)
        # 24 original, 26 opponent, exact pre-tip midpoint = 25.
        self.assertEqual(observed["large_misses"][0]["projection"],25)

    def test_missing_or_ambiguous_final_not_attached(self):
        frozen=snapshot([market()],AT)
        bad={**game(),"final_confirmed":False}
        result=settle(frozen,[bad],"2026-11-13T04:00:00Z")
        self.assertEqual(result[0]["status"],"PENDING")
        self.assertNotIn("actual_minutes",result[0])
        wrong={**game(),"opponent":"NYK"}
        result=settle(frozen,[wrong],"2026-11-13T04:00:00Z")
        self.assertEqual(result[0]["status"],"PENDING")

    def test_thresholds_vary_by_market(self):
        p=market("AST")
        p["projection"]=7
        p["combined_projection"]=7
        p["book_quotes"][0]["line"]=6.5
        finished=settle(snapshot([p],AT),[game(minutes=30,points=30)],
                        "2026-11-13T04:00:00Z")
        self.assertEqual(report(finished)["by_market"]["AST"]["extreme"]["markets"],1)

if __name__=="__main__":unittest.main()

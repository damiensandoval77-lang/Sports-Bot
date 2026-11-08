import unittest
from iphone_bot.unified_reliability_research import view

START="2026-11-08T01:00:00Z"
CAPTURE="2026-11-07T19:00:00Z"

def row(pid="123"):
    return {"event_start":START,"captured_at":CAPTURE,"player_id":pid,
        "player":"Example","team":"BOS","market":"PTS",
        "combined_projection":23.,"sanity_shadow_v1":{
            "status":"SHADOW_CANDIDATE_UNVALIDATED",
            "warnings":["LARGE_SEASON_BASELINE_DEVIATION"]},
        "stress_test_20k_v1":{"status":"CONDITIONAL_STRESS_RESEARCH_ONLY",
            "warnings":[],"fragile_high_confidence":False},
        "model_disagreement_v1":{"status":"RESEARCH_MODEL_AGREEMENT","flags":[]}}

class UnifiedReliabilityResearchTests(unittest.TestCase):
    def test_warns_on_sanity_large_deviation(self):
        r=view([row()],[],generated_at=CAPTURE)
        self.assertEqual(r["classification_counts"]["NEEDS_REVIEW"],1)
        self.assertEqual(r["recent_markets"][0]["reasons"],
                         ["SANITY_LARGE_SEASON_BASELINE_DEVIATION"])
        self.assertTrue(r["no_live_picks_changed"])

    def test_missing_and_partial_old_models_are_not_clean(self):
        previous=row()
        del previous["stress_test_20k_v1"]
        r=view([previous],[],generated_at=CAPTURE)
        self.assertIn("MISSING_FROZEN_STRESS_TEST_20K_V1",
                      r["recent_markets"][0]["reasons"])
        self.assertNotEqual(r["recent_markets"][0]["classification"],
                            "NO_RESEARCH_FLAGS_UNVALIDATED")

    def test_stress_fragility_review_and_disagreement(self):
        x=row()
        x["sanity_shadow_v1"]["warnings"]=[]
        x["stress_test_20k_v1"]["fragile_high_confidence"]=True
        x["model_disagreement_v1"]={"status":"MODEL_DISAGREEMENT_REVIEW",
            "flags":["ORIGINAL_OPPONENT_DIRECTION_CONFLICT"]}
        y=view([x],[],generated_at=CAPTURE)
        self.assertIn("STRESS_FRAGILE_HIGH_SIMULATED_CONFIDENCE",
                      y["recent_markets"][0]["reasons"])
        self.assertIn("MODELS_ORIGINAL_OPPONENT_DIRECTION_CONFLICT",
                      y["recent_markets"][0]["reasons"])
        self.assertEqual(y["classification_counts"]["NEEDS_REVIEW"],1)

    def test_unchanged_and_complete_is_not_verified_confidence(self):
        x=row()
        x["sanity_shadow_v1"]["warnings"]=[]
        y=view([x],[],generated_at=CAPTURE)
        self.assertEqual(y["classification_counts"]["NO_RESEARCH_FLAGS_UNVALIDATED"],1)
        self.assertTrue(y["unverified_clean_does_not_mean_safe"])
        self.assertFalse(y["confidence_proxy_quote_coverage"]["confidence_calibrated"])

    def test_pretip_first_capture_wins_without_backfill(self):
        early=row()
        late=row()
        late["captured_at"]="2026-11-07T20:00:00Z"
        late["sanity_shadow_v1"]["warnings"]=[]
        report=view([late,early],[],generated_at=CAPTURE)
        self.assertEqual(report["independent_research_markets"],1)
        self.assertEqual(report["classification_counts"]["NEEDS_REVIEW"],1)
        self.assertEqual(report["excluded_records"]["duplicate_capture"],1)

    def test_after_tipoff_not_scored(self):
        x=row()
        x["captured_at"]="2026-11-08T02:00:00Z"
        z=view([x],[],generated_at=CAPTURE)
        self.assertEqual(z["independent_research_markets"],0)
        self.assertEqual(z["excluded_records"]["late_or_not_pregame"],1)

    def test_never_backfills_or_relabels_old_settled_quotes(self):
        x=row()
        p=[{"status":"SETTLED","combined_probability_proxy_estimate":.95,
            "event_start":START,"captured_at":CAPTURE,"market":"PTS"}]
        z=view([x],p,generated_at=CAPTURE)
        self.assertEqual(z["confidence_proxy_quote_coverage"]["valid_pregame_quote_snapshots"],0)
        self.assertEqual(z["confidence_proxy_quote_coverage"]["settled_quote_snapshots_with_frozen_proxy"],0)
        self.assertFalse(z["confidence_proxy_quote_coverage"]["confidence_calibrated"])

    def test_no_data_does_not_claim_improvement(self):
        z=view([],[],generated_at=CAPTURE)
        self.assertEqual(z["independent_research_markets"],0)
        self.assertTrue(z["no_accuracy_improvement_claimed"])

if __name__=="__main__":
    unittest.main()

import unittest
from iphone_bot.model_disagreement_research import detect,report
from iphone_bot.paper_pick_pipeline import utc

def check(**updates):
    kw={"market":"PTS","line":25.5,"original":27,"opponent":23,
        "combined":25,"sanity":24,"opponent_verified":True,
        "sanity_status":"SHADOW_CANDIDATE_UNVALIDATED"}
    kw.update(updates)
    return detect(**kw)

class ModelDisagreementResearchTests(unittest.TestCase):
    def test_original_opponent_conflict(self):
        x=check()
        self.assertEqual(x["status"],"MODEL_DISAGREEMENT_REVIEW")
        self.assertIn("ORIGINAL_OPPONENT_DIRECTION_CONFLICT",x["flags"])
        self.assertIn("MATERIAL_ORIGINAL_OPPONENT_SPREAD",x["flags"])
        self.assertEqual(x["independent_models_available"],2)
        self.assertFalse(x["pick_changed"])
        self.assertFalse(x["probability_changed"])

    def test_opponent_missing_is_not_an_agreement(self):
        x=check(opponent=None,opponent_verified=False)
        self.assertEqual(x["status"],"PARTIAL_MODEL_COVERAGE")
        self.assertEqual(x["independent_models_available"],1)
        self.assertIn("OPPONENT_MODEL_UNAVAILABLE",x["flags"])

    def test_unverified_opponent_never_counts_as_independent(self):
        x=check(opponent=100,opponent_verified=False)
        self.assertIsNone(x["projections"]["opponent_aware"])
        self.assertEqual(x["status"],"PARTIAL_MODEL_COVERAGE")

    def test_derived_combined_is_not_third_vote(self):
        x=check(original=20,opponent=30,combined=25)
        self.assertEqual(x["independent_models_available"],2)

    def test_sanity_unavailable_not_silently_imputed(self):
        x=check(original=25,opponent=25.2,combined=25.1,
                sanity=None,sanity_status="REVIEW_ONLY_UNCERTAIN_INPUTS")
        self.assertEqual(x["status"],"TWO_MODEL_AGREEMENT_SHADOW_MISSING")
        self.assertIsNone(x["projections"]["sanity_shadow"])

    def test_sanity_conflicts_with_combined(self):
        x=check(original=27,opponent=27.2,combined=27.1,sanity=22)
        self.assertIn("SANITY_COMBINED_DIRECTION_CONFLICT",x["flags"])

    def test_thresholds_are_market_specific_and_undecided_side(self):
        x=check(market="AST",line=8.5,original=8.5,opponent=10,
                combined=9.25,sanity=9)
        self.assertEqual(x["directions"]["original"],"AT_LINE")
        self.assertIn("MATERIAL_ORIGINAL_OPPONENT_SPREAD",x["flags"])

    def test_nonfinite_input_fails_closed(self):
        self.assertEqual(check(original=float("nan"))["status"],"PARTIAL_MODEL_COVERAGE")
        self.assertEqual(check(combined=float("inf"))["status"],"INVALID_OR_UNSUPPORTED_INPUT")
        self.assertEqual(check(market="UNKNOWN")["status"],"INVALID_OR_UNSUPPORTED_INPUT")

    def test_frozen_report_requires_pretip_and_exact_outcome(self):
        event="2026-11-08T01:00:00Z"
        capture="2026-11-07T19:00:00Z"
        def row(pid,flagged,late=False):
            return {"player_id":pid,"market":"PTS","event_start":event,
                "captured_at":event if late else capture,
                "combined_projection":25.0,
                "model_disagreement_v1":{
                    "status":"MODEL_DISAGREEMENT_REVIEW" if flagged
                             else "RESEARCH_MODEL_AGREEMENT",
                    "flags":["ORIGINAL_OPPONENT_DIRECTION_CONFLICT"] if flagged else []}}
        paper=[{"status":"SETTLED","player_id":pid,"market":"PTS",
            "event_start":event,"captured_at":capture,"actual":actual}
            for pid,actual in (("1",21),("2",24),("3",31))]
        def independent(rows):
            return rows
        rows=[row("1",True),row("2",False),row("3",True,late=True)]
        out=report(rows,paper,independent,utc)
        self.assertEqual(out["flagged_settled"]["paired_markets"],1)
        self.assertEqual(out["unflagged_settled"]["paired_markets"],1)
        self.assertEqual(out["flag_counts"]["ORIGINAL_OPPONENT_DIRECTION_CONFLICT"],1)
        self.assertFalse(out["model_improvement_established"])
        self.assertEqual(report(rows+[rows[0]],paper,independent,utc)["flagged_settled"],out["flagged_settled"])

    def test_no_backfilling_missing_research_record(self):
        x=report([{"player_id":"1"}],[],lambda v:v,utc)
        self.assertEqual(x["flagged_settled"]["paired_markets"],0)
        self.assertFalse(x["live_picks_changed"])

if __name__=="__main__":
    unittest.main()

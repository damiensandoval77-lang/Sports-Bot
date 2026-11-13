"""Research promotion is always blocked without fresh, audited evidence."""
import unittest
try:
    from iphone_bot.external_stats_research_gate import readiness
except ImportError:
    from external_stats_research_gate import readiness


def paper(days=2, n=592, hit=0.4764, roi=-0.1338):
    return {"performance":{"models":{"combined":{
        "direction_eligible":n, "direction_hit_rate":hit,
        "paper_roi_per_priced_unit":roi}}},
        "accuracy_feedback":{"overall":{"overall":{"distinct_game_dates":days}}}}


def paired(n=100, days=10):
    return {"status":"PAIRED_SHADOW_RESEARCH_ONLY", "production_modified":False,
            "automatic_promotion":False, "paired_rows":n,
            "unique_event_dates":days}


class ResearchGateTests(unittest.TestCase):
    def test_real_world_like_low_hit_and_two_dates_blocked(self):
        result=readiness(paper())
        self.assertFalse(result["promotion_allowed"])
        self.assertFalse(result["production_modified"])
        self.assertIn("INSUFFICIENT_INDEPENDENT_SETTLED_GAME_DATES",result["reason_codes"])
        self.assertIn("NO_DEMONSTRATED_POSITIVE_PAPER_PERFORMANCE",result["reason_codes"])
        self.assertEqual(result["observed_baseline"]["combined_direction_hit_rate"],0.4764)

    def test_no_automated_promotion_even_if_all_gates_met(self):
        result=readiness(paper(days=20,n=1000,hit=.65,roi=.15),paired(1000,20))
        self.assertFalse(result["promotion_allowed"])
        self.assertTrue(result["paired_comparison_gate_met"])
        self.assertIn("REQUIRES_PROSPECTIVE_HUMAN_REVIEW_AND_CALIBRATION", result["reason_codes"])

    def test_paired_unavailable(self):
        result=readiness(paper(days=20,n=1000,hit=.65,roi=.15))
        self.assertIn("NO_SUFFICIENT_POINT_IN_TIME_PAIRED_CHALLENGER",result["reason_codes"])

    def test_bad_paired_production_mutation(self):
        p=paired(200,20)
        p["production_modified"]=True
        result=readiness(paper(days=20,n=1000,hit=.65,roi=.15),p)
        self.assertFalse(result["paired_comparison_gate_met"])

    def test_missing_paper_metrics(self):
        result=readiness({})
        self.assertIsNone(result["observed_baseline"]["combined_direction_hit_rate"])
        self.assertFalse(result["promotion_allowed"])

    def test_non_finite_rejected(self):
        result=readiness(paper(days=50,n=900,hit=float("nan"),roi=.2),paired(300,30))
        self.assertIn("INSUFFICIENT_OR_INVALID_GRADED_BASELINE",result["reason_codes"])


if __name__=="__main__":
    unittest.main()

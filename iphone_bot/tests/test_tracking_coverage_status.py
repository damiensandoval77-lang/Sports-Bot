import unittest
from iphone_bot.tracking_coverage_status import summarize

class CoverageAuditTests(unittest.TestCase):
    def test_no_board_does_not_imply_poor_accuracy(self):
        r=summarize({"status":"EXPERIMENTAL_NON_CALIBRATED","comparisons":[]},
                    {"tracking_opportunity_shadow":{"by_market":{}}},
                    {"status":"NOT_CONFIGURED_NEEDS_PROVIDER_TOKEN"})
        self.assertEqual(r["status"],"NO_AUTHORIZED_GAMELEVEL_TRACKING")
        self.assertTrue(r["current_board_empty"])
        self.assertTrue(r["no_current_board_is_not_zero_accuracy"])
        self.assertEqual(r["by_market"]["AST"]["current_board_models"],0)
        self.assertEqual(r["by_market"]["REB"]["confirmed_tracking_coverage"],0)
    def test_count_available_prop_markets_without_confusing_with_frozen_shadows(self):
        board={"status":"EXPERIMENTAL_NON_CALIBRATED",
         "comparisons":[{"stat":"AST"},{"stat":"REB"},{"stat":"PTS"},{"stat":"REB"}]}
        research={"tracking_opportunity_shadow":{"by_market":{
          "AST":{"paired_markets":3,"exact_line_eligible":2},
          "REB":{"paired_markets":4,"exact_line_eligible":3}}}}
        r=summarize(board,research,{"status":"NOT_CONFIGURED_NEEDS_PROVIDER_TOKEN"})
        self.assertEqual(r["by_market"]["AST"]["current_board_models"],1)
        self.assertEqual(r["by_market"]["REB"]["current_board_models"],2)
        self.assertEqual(r["by_market"]["AST"]["genuinely_graded_tracking_shadows"],3)
        self.assertEqual(r["by_market"]["AST"]["grade_eligible_exact_line"],2)
        self.assertFalse(r["real_tracking_accuracy_improvement_proven"])

if __name__=="__main__":unittest.main()

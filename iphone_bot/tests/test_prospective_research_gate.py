import unittest
from iphone_bot.prospective_research_gate import verify,inspect

def row():
    return {"event_start":"2026-11-08T01:00:00+00:00",
      "sanity_shadow_v1":{"status":"INSUFFICIENT_PREGAME_HISTORY"},
      "stress_test_20k_v1":{"status":"INVALID_OR_MISSING_INPUTS",
                             "warnings":["MISSING_VALID_FORECAST_LINE_OR_MINUTES"]},
      "model_disagreement_v1":{"status":"PARTIAL_MODEL_COVERAGE",
                               "flags":["OPPONENT_MODEL_UNAVAILABLE"]}}

class ProspectiveResearchGateTests(unittest.TestCase):
    def test_insufficient_input_is_still_a_real_frozen_diagnostic(self):
        r=verify([row()],0,1)
        self.assertTrue(r["all_new_rows_have_three_diagnostics"])
        self.assertEqual(r["new_research_rows"],1)
        self.assertEqual(r["by_diagnostic_status"]["stress_test_20k_v1"]["INVALID_OR_MISSING_INPUTS"],1)
        self.assertTrue(r["missing_input_status_is_not_calibrated_confidence"])
    def test_legacy_missing_data_is_not_fake_retroactively_completed(self):
        old={"event_start":"2026-10-29T00:00:00+00:00"}
        r=verify([old,row()],1,2)
        self.assertEqual(r["new_research_rows"],1)
        self.assertEqual(r["missing_by_field"],{})
        self.assertNotIn("sanity_shadow_v1",old)
    def test_new_diagnostic_missing_must_fail(self):
        broken=row()
        del broken["model_disagreement_v1"]
        with self.assertRaisesRegex(AssertionError,"model_disagreement_v1"):
            verify([broken],0,1)
    def test_missing_status_must_fail_even_if_dict_exists(self):
        broken=row()
        broken["stress_test_20k_v1"]={}
        with self.assertRaisesRegex(AssertionError,"stress_test_20k_v1"):
            verify([broken],0,1)
    def test_empty_fresh_capture_does_not_pretend_more_rows(self):
        r=inspect([row()],1,1)
        self.assertEqual(r["new_research_rows"],0)
        self.assertTrue(r["all_new_rows_have_three_diagnostics"])
    def test_negative_ledger_growth_rejected(self):
        with self.assertRaises(ValueError):verify([],5,3)
if __name__=="__main__":unittest.main()

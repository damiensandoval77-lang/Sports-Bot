import unittest
from iphone_bot.verify_paper_settlement_voids import verify

def void():
    return {"status":"VOID_DNP","result":"VOID","void_reason":"INACTIVE",
            "void_source_url":"https://www.nba.com/game/0022600030",
            "void_recorded_at":"2026-11-10T05:00:00+00:00"}

class FinalVoidTests(unittest.TestCase):
    def test_provenance_verified_voids_are_accounted_but_not_graded(self):
        rows=[void(),{"status":"SETTLED","result":"WIN"},{"status":"PENDING"}]
        result=verify(rows,{"void_dnp":1})
        self.assertEqual(result["VOID_DNP"],1)
        self.assertEqual(result["SETTLED"],1)
    def test_mismatched_void_count_is_not_ignored(self):
        with self.assertRaisesRegex(ValueError,"NBA_DNP_VOID_COUNT_MISMATCH"):
            verify([void()],{"void_dnp":0})
    def test_undocumented_void_is_rejected(self):
        for changes in [
            {"result":"LOSS"},
            {"void_reason":""},
            {"void_source_url":"https://example.com/anything"},
            {"void_source_url":"https://www.nba.com/game/"},
            {"void_recorded_at":None},
        ]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    verify([{**void(),**changes}],{"void_dnp":1})
    def test_unknown_status_does_not_pass(self):
        with self.assertRaisesRegex(ValueError,"UNKNOWN_FROZEN_STATUS"):
            verify([{"status":"VOID_UNVERIFIED"}],{"void_dnp":0})
    def test_missing_timezone_does_not_pass(self):
        with self.assertRaisesRegex(ValueError,"NBA_DNP_VOID_MISSING_RECORD_TIMESTAMP"):
            verify([{**void(),"void_recorded_at":"2026-11-10T05:00:00"}],{"void_dnp":1})
if __name__=="__main__":unittest.main()

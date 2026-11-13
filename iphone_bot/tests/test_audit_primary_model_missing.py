import datetime as dt
import unittest
from iphone_bot.audit_primary_model_missing import audit

NOW=dt.datetime(2026,11,10,19,tzinfo=dt.timezone.utc)
DAY="2026-11-10"
def quote(line,player="Example"):
    return {"game":"Boston Celtics @ Philadelphia 76ers","player":player,"team":"BOS",
            "stat":"PTS","line":line,"starts_at":"2026-11-11T01:00:00Z",
            "start":"2026-11-11T01:00:00Z",
            "source":"independent_prizepicksapi_com","is_demo":False,
            "tier":"standard","pickem_tier":"standard",
            "standard_line_two_sided_verified":True}
def run(quotes,locks,live=(),research=()):
    return audit({"quotes":quotes},
                 {"records":locks},
                 {"predictions":live},
                 {"records":research},DAY,NOW)
class CaptureReasons(unittest.TestCase):
    def test_moved_line_does_not_replace_frozen_original(self):
        initial=quote(24.5)
        moved=quote(25.5)
        result=run([moved],[initial],[moved])
        self.assertEqual(result["missing_by_cause"],{"MOVED_ORIGINAL_STANDARD_THRESHOLD":1})
        self.assertEqual(result["details"][0]["safe_action"],
                         "PRESERVE_ORIGINAL_FROZEN_LINE_AND_RESEARCH_VERSION")

    def test_new_player_model_exists_but_missing_primary_freeze(self):
        fresh=quote(20.5,player="Other")
        result=run([fresh],[],[fresh])
        self.assertEqual(result["missing_by_cause"],{"MODEL_EXISTS_BUT_PRIMARY_FREEZE_MISSING":1})

    def test_missing_validated_model_cannot_use_research_as_primary(self):
        row=quote(10.5,player="New Player")
        research={**row,"more_tier":"standard","less_tier":"standard","research_only":True}
        out=run([row],[],[],[research])
        self.assertEqual(out["missing_by_cause"],{"NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET":1})
        self.assertTrue(out["details"][0]["separate_research_receipt"])
        self.assertEqual(out["status"],"PRIMARY_STANDARD_CAPTURE_INCOMPLETE")

    def test_only_standard_verified_quotes_enter_gap_math(self):
        row=quote(18.5)
        wrong={**row,"tier":"demon"}
        out=run([row,wrong],[row])
        self.assertEqual(out["status"],"PRIMARY_STANDARD_CAPTURE_VERIFIED")
        self.assertEqual(out["unmatched_exact_standard_thresholds"],0)

if __name__=="__main__":
    unittest.main()

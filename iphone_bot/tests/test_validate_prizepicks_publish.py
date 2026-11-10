import datetime as dt
import copy
import unittest
from iphone_bot.validate_prizepicks_publish import validate
NOW=dt.datetime(2026,11,10,0,0,tzinfo=dt.timezone.utc)
ROW={"id":"pp1","player":"Player A","game":"A @ B","source":"independent_prizepicksapi_com",
     "is_demo":False,"starts_at":"2026-11-10T01:00:00Z","line":20.5,"more_tier":"standard"}
def fixtures():
    raw={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES","generated_at":"2026-11-09T23:55:00Z",
         "board_offers":[copy.deepcopy(ROW)],"partial_board":True,"complete_provider_board":False,
         "board_coverage_scope":"NBA_ACTIVE_STANDARD_TIER_ONLY"}
    site={"status":raw["status"],"source":"independent_prizepicksapi_com","generated_at":raw["generated_at"],
          "board_offers":[copy.deepcopy(ROW)],"independent_board_count":1,
          "partial_board":True,"complete_provider_board":False,
          "board_coverage_scope":"NBA_ACTIVE_STANDARD_TIER_ONLY"}
    model={"source":"AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS","source_generated_at":raw["generated_at"],
           "real_american_odds_provided":False,"status":"FRESH_AUTHENTIC_PRIZEPICKS_LINES",
           "is_live":True,"picks":[{"player":"Player A"}]}
    return raw,site,model
class PublishGateTests(unittest.TestCase):
    def test_valid_partial_board(self):
        self.assertEqual(validate(*fixtures(),now=NOW),[])
    def test_legacy_provider_scope_cannot_claim_complete_standard_board(self):
        a,b,c=fixtures()
        a["complete_provider_board"]=True
        b["complete_provider_board"]=True
        a["partial_board"]=False
        b["partial_board"]=False
        a["board_coverage_scope"]="UNVERIFIED_LEGACY_SCOPE"
        b["board_coverage_scope"]="UNVERIFIED_LEGACY_SCOPE"
        self.assertIn("STANDARD_BOARD_COMPLETENESS_NOT_VERIFIED",validate(a,b,c,now=NOW))
    def test_mismatched_source_scope_is_rejected(self):
        a,b,c=fixtures()
        b["board_coverage_scope"]="UNVERIFIED_LEGACY_SCOPE"
        self.assertIn("PROVIDER_SCOPE_MISREPORTED",validate(a,b,c,now=NOW))

    def test_empty_does_not_overwrite(self):
        a,b,c=fixtures();b["board_offers"]=[];self.assertTrue(validate(a,b,c,now=NOW))
    def test_missing_offer_rejected(self):
        a,b,c=fixtures();a["board_offers"].append({**ROW,"id":"pp2"});self.assertIn("VERIFIED_OFFER_COUNT_MISMATCH",validate(a,b,c,now=NOW))
    def test_modified_offer_id_rejected(self):
        a,b,c=fixtures();b["board_offers"][0]["id"]="fake";self.assertIn("OFFER_IDENTITIES_CHANGED_OR_MISSING",validate(a,b,c,now=NOW))
    def test_changed_line_rejected(self):
        a,b,c=fixtures();b["board_offers"][0]["line"]=19.5
        self.assertIn("EXPORTED_OFFER_DIFFERS_FROM_VERIFIED_SOURCE",validate(a,b,c,now=NOW))
    def test_fake_line_rejected(self):
        a,b,c=fixtures();b["board_offers"][0]["line"]=float("nan");self.assertIn("INVALID_EXPORTED_LINE",validate(a,b,c,now=NOW))
    def test_stale_rejected(self):
        a,b,c=fixtures();self.assertIn("SOURCE_TIMESTAMP_INVALID_OR_STALE",validate(a,b,c,now=NOW+dt.timedelta(hours=10)))
    def test_model_fabrication_rejected(self):
        a,b,c=fixtures();c["picks"]=[];self.assertIn("MODEL_READY_WITHOUT_MATCHED_SOURCE",validate(a,b,c,now=NOW))
    def test_completeness_mislabel_rejected(self):
        a,b,c=fixtures();b["complete_provider_board"]=True;self.assertIn("PROVIDER_COMPLETENESS_MISREPORTED",validate(a,b,c,now=NOW))
    def test_invalid_source_rejected(self):
        a,b,c=fixtures();a["status"]="ERROR";self.assertIn("UNVERIFIED_PROVIDER_STATUS",validate(a,b,c,now=NOW))
if __name__=="__main__":
    unittest.main()

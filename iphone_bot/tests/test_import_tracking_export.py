import unittest
from iphone_bot.import_tracking_export import normalize

def approval():
    return {"season":"2026-27","source":"TEST_NONPRODUCTION_PROVIDER",
       "generated_at":"2026-11-07T05:00:00Z",
       "allowed_use":"NBA_PROP_RESEARCH",
       "reviewer_confirmation":"MANUALLY_VERIFIED",
       "permission_reference":"FICTIONAL_FIXTURE_ONLY"}
def rows():
    return [{"player_id":"10","team":"BOS","game_id":"0022600123",
     "game_date":"2026-11-05","observed_at":"2026-11-06T04:00:00Z",
     "minutes":"30","potential_assists":"12","assists":"6",
     "rebound_chances":"16","rebounds":"8"}]

class PrivateTrackingImportTests(unittest.TestCase):
    def test_full_private_data_contract_and_numeric_rows(self):
        data=normalize(rows(),approval())
        self.assertEqual(data["status"],"AUTHORIZED_TRACKING_RESEARCH")
        self.assertEqual(data["observations"][0]["potential_assists"],12.)
        self.assertEqual(data["observations"][0]["rebound_chances"],16.)
        self.assertEqual(data["observations"][0]["minutes"],30.)
    def test_reject_permission_and_future_data(self):
        m=approval();m["allowed_use"]="EDITORIAL"
        with self.assertRaisesRegex(ValueError,"rights"):normalize(rows(),m)
        r=rows();r[0]["observed_at"]="2026-11-09T04:00:00Z"
        with self.assertRaisesRegex(ValueError,"observation"):normalize(r,approval())
    def test_reject_duplicates_invalid_chance_counts(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            normalize(rows()+rows(),approval())
        r=rows();r[0]["rebounds"]="20"
        with self.assertRaisesRegex(ValueError,"chance counts"):
            normalize(r,approval())
        with self.assertRaisesRegex(ValueError,"No real"):
            normalize([],approval())

if __name__=="__main__":unittest.main()

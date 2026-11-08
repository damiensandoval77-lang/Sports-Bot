"""No PBP Stats API call; permission and identity-gated private import."""
import unittest
from iphone_bot.import_authorized_onoff import validate

def source():
    return {"season":"2026-27","source":"AUTHORIZED_TEST_EXPORT",
        "generated_at":"2026-11-07T18:00:00Z",
        "observations":[{
          "player_id":"100","teammate_id":"900","team":"BOS",
          "data_through":"2026-11-06",
          "observed_through_at":"2026-11-07T17:00:00Z",
          "with":{"games":6,"minutes":140,
                  "PTS_per36":20,"REB_per36":5,"AST_per36":4},
          "without":{"games":6,"minutes":180,
                  "PTS_per36":26,"REB_per36":7,"AST_per36":6}}]}

def approval():
    return {"reviewed_for_betting_analytics":True,
      "allowed_use":"NBA_PROP_RESEARCH","reviewer_confirmation":"MANUALLY_VERIFIED",
      "permission_reference":"TEST_FIXTURE_ONLY"}

def roster():
    return {"players":[{"player_id":"100","team":"BOS"},
                       {"player_id":"900","team":"BOS"}]}

class ImportTest(unittest.TestCase):
    def test_normalized_valid_private_export(self):
        out=validate(source(),approval(),roster())
        self.assertEqual(out["status"],"LICENSED_ON_OFF_VERIFIED")
        self.assertEqual(out["observations"][0]["without"]["AST_per36"],6)
        self.assertEqual(out["observations"][0]["season"],"2026-27")
    def test_refuse_unpermitted_use_and_incomplete_ids(self):
        p=approval();p["allowed_use"]="EDITORIAL_ONLY"
        with self.assertRaisesRegex(ValueError,"permitted use"):
            validate(source(),p,roster())
        with self.assertRaisesRegex(ValueError,"roster"):
            validate(source(),approval(),{"players":[{"player_id":"100","team":"BOS"}]})
    def test_reject_duplicate_ambiguous_and_future_observations(self):
        d=source()
        d["observations"].append(d["observations"][0])
        with self.assertRaisesRegex(ValueError,"duplicate"):
            validate(d,approval(),roster())
        d=source();d["observations"][0]["data_through"]="2026-11-08"
        with self.assertRaisesRegex(ValueError,"cutoff"):
            validate(d,approval(),roster())
        d=source();d["observations"][0]["with"]["minutes"]=25
        with self.assertRaisesRegex(ValueError,"insufficient"):
            validate(d,approval(),roster())
    def test_reject_export_without_observations(self):
        d=source();d["observations"]=[]
        with self.assertRaisesRegex(ValueError,"No actual"):
            validate(d,approval(),roster())

if __name__=="__main__":unittest.main()

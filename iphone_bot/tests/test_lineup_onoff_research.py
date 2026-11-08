"""WOWY source rights, provenance, IDs, samples, and future isolation."""
import copy
import unittest
from iphone_bot.lineup_onoff_research import evaluate

NOW="2026-11-07T19:00:00Z"
TIP="2026-11-08T01:00:00Z"

def feed():
    return {"status":"LICENSED_ON_OFF_VERIFIED","licensed_use_verified":True,
        "source":"TEST_LICENSED_FIXTURE","generated_at":"2026-11-07T18:00:00Z",
        "authorization":{"reviewed_for_betting_analytics":True,
          "allowed_use":"NBA_PROP_RESEARCH","reviewer_confirmation":"MANUALLY_VERIFIED",
          "permission_reference":"TEST_ONLY_NONPRODUCTION_FIXTURE"},
        "observations":[{"player_id":"100","teammate_id":"900","team":"BOS",
            "season":"2026-27","data_through":"2026-11-06",
            "observed_through_at":"2026-11-07T17:00:00Z",
            "with":{"games":8,"minutes":220,"PTS_per36":19,"REB_per36":6,"AST_per36":4},
            "without":{"games":7,"minutes":230,"PTS_per36":25,"REB_per36":8,"AST_per36":6}}]}

def check(data=None,market="PTS",**kwargs):
    args=dict(player_id="100",teammate_id="900",team="BOS",market=market,
              baseline=20,expected_minutes=30,game_start=TIP,captured_at=NOW)
    args.update(kwargs)
    return evaluate(feed() if data is None else data,**args)

class LicensedOnOffResearchTests(unittest.TestCase):
    def test_fixed_bounded_pretip_shadow_all_markets(self):
        self.assertAlmostEqual(check()["projection"],21.25)
        self.assertAlmostEqual(check(market="REB")["projection"],20.4167,places=3)
        self.assertAlmostEqual(check(market="AST")["projection"],20.4167,places=3)
        self.assertAlmostEqual(check(market="PRA")["projection"],21.6)
        self.assertEqual(check()["with_games"],8)
        self.assertFalse(check()["production_applied"])
    def test_rights_and_player_identity_fail_closed(self):
        d=feed();d["licensed_use_verified"]=False
        self.assertIsNone(check(d)["projection"])
        self.assertIsNone(check(player_id="101")["projection"])
        self.assertIsNone(check(team="NYK")["projection"])
        self.assertIsNone(check(teammate_id="901")["projection"])
        d=feed();d["observations"].append(copy.deepcopy(d["observations"][0]))
        self.assertEqual(check(d)["status"],"MISSING_OR_AMBIGUOUS_PLAYER_TEAM_PAIR")
    def test_future_stats_and_status_fail_closed(self):
        d=feed();d["observations"][0]["data_through"]="2026-11-07"
        self.assertEqual(check(d)["status"],"SPLIT_INCLUDES_TARGET_GAME")
        d=feed();d["generated_at"]="2026-11-08T02:00:00Z"
        self.assertEqual(check(d)["status"],"UNSAFE_CAPTURE_OR_FEED_TIMESTAMP")
        self.assertEqual(check(game_start="2026-11-07T17:00:00Z")["status"],
                         "UNSAFE_CAPTURE_OR_FEED_TIMESTAMP")
    def test_authorization_manifest_and_source_time_are_mandatory(self):
        d=feed()
        d.pop("authorization")
        self.assertEqual(check(d)["status"],"MISSING_VERIFIED_USAGE_PERMISSION")
        d=feed()
        d["authorization"]["allowed_use"]="EDITORIAL_ONLY"
        self.assertEqual(check(d)["status"],"MISSING_VERIFIED_USAGE_PERMISSION")
        d=feed()
        d["observations"][0].pop("observed_through_at")
        self.assertEqual(check(d)["status"],"MISSING_SOURCE_OBSERVATION_TIMESTAMP")
        d=feed()
        d["observations"][0]["observed_through_at"]="2026-11-08T01:00:00Z"
        self.assertEqual(check(d)["status"],"UNSAFE_SOURCE_OBSERVATION_TIMESTAMP")

    def test_tiny_samples_or_missing_rates_are_rejected(self):
        d=feed();d["observations"][0]["without"]["minutes"]=15
        self.assertEqual(check(d)["status"],"INSUFFICIENT_ON_OFF_SAMPLE")
        d=feed();del d["observations"][0]["without"]["PTS_per36"]
        self.assertEqual(check(d)["status"],"MISSING_PER36_RATE")
        d=feed();d["observations"][0]["without"]["PTS_per36"]=300
        self.assertLessEqual(check(d)["projection"],21.6)
    def test_disabled_placeholder_is_not_live_data(self):
        self.assertIsNone(check({"status":"AWAITING_LICENSED_PROVIDER_ACCESS"})["projection"])

if __name__=="__main__":unittest.main()

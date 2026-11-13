import unittest
from datetime import datetime,timezone
try:
    from iphone_bot.injury_refresh_watchdog import decision
except ImportError:
    from injury_refresh_watchdog import decision
NOW=datetime(2026,11,9,23,30,tzinfo=timezone.utc)
def official(t="2026-11-09T23:15:00Z"):
    return {"status":"OFFICIAL_NBA_REPORT_VERIFIED","injury_data_verified":True,
       "report_issued_at":t}
def model(t="2026-11-09T23:15:00Z"):
    return {"status":"LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED",
        "generated_at":"2026-11-09T23:20:00Z","official_report_issued_at":t}
def slate(state="pre",time="2026-11-10T01:00:00Z"):
    return {"games":[{"game_state":state,"start":time}]}
class InjuryWatchdogTests(unittest.TestCase):
    def test_does_not_waste_model_refresh_when_versions_match(self):
        self.assertFalse(decision(official(),model(),slate(),NOW)["needs_refresh"])
    def test_recovers_when_newer_report_not_modeled(self):
        r=decision(official("2026-11-09T23:25:00Z"),model(),slate(),NOW)
        self.assertTrue(r["needs_refresh"])
        self.assertEqual(r["reason"],"NEWER_OFFICIAL_REPORT_NOT_MODELED")
    def test_no_future_match_no_rebuild(self):
        self.assertFalse(decision(official("2026-11-09T23:25:00Z"),model(),
              slate("post"),NOW)["needs_refresh"])
    def test_missing_model_detected(self):
        self.assertTrue(decision(official(),{},slate(),NOW)["needs_refresh"])
    def test_unverified_source_never_rebuilds(self):
        self.assertFalse(decision({"status":"THIRD_PARTY_ESPN_INJURY_CONTEXT"},
            model(),slate(),NOW)["needs_refresh"])
if __name__=="__main__":unittest.main()

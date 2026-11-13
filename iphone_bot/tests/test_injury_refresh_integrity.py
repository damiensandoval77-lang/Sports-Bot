import unittest
from datetime import datetime,timezone
try:
    from iphone_bot.injury_refresh_integrity import integrity
except ImportError:
    from injury_refresh_integrity import integrity
NOW=datetime(2026,11,9,23,30,tzinfo=timezone.utc)
def report(t="2026-11-09T23:15:00Z"):
    return {"status":"OFFICIAL_NBA_REPORT_VERIFIED","injury_data_verified":True,"report_issued_at":t}
def model(t="2026-11-09T23:15:00Z"):
    return {"status":"LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED",
      "generated_at":"2026-11-09T23:20:00Z","official_report_issued_at":t}
class InjuryIntegrityTests(unittest.TestCase):
    def test_latest_report_published_is_safe(self):
        self.assertTrue(integrity(report(),model(),NOW)["safe"])
    def test_report_changes_mid_training_fail_closed(self):
        r=integrity(report("2026-11-09T23:25:00Z"),model(),NOW)
        self.assertFalse(r["safe"])
        self.assertEqual(r["reason"],"NEWER_OFFICIAL_REPORT_NOT_MODELED")
    def test_missing_stamp_fails_closed(self):
        m=model()
        del m["official_report_issued_at"]
        self.assertFalse(integrity(report(),m,NOW)["safe"])
    def test_future_broken_model_fails_closed(self):
        m=model()
        m["generated_at"]="2026-11-10T00:30:00Z"
        self.assertFalse(integrity(report(),m,NOW)["safe"])
    def test_unverified_espn_backup_cannot_override_official(self):
        backup={"status":"THIRD_PARTY_ESPN_INJURY_CONTEXT",
            "injury_data_verified":False,"report_issued_at":"2026-11-09T23:25:00Z"}
        self.assertTrue(integrity(backup,model(),NOW)["safe"])
if __name__=="__main__":unittest.main()

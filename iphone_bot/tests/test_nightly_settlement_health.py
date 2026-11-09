import datetime as dt
import unittest
from iphone_bot.nightly_settlement_health import health

UTC=dt.timezone.utc
NOW=dt.datetime(2026,11,9,16,0,tzinfo=UTC)
DAY_START="2026-11-09T00:00:00Z"
def row(status="PENDING",start=DAY_START):
    return {"status":status,"start":start,"game":"Away @ Home",
            "player":"Example","player_id":"101","stat":"PTS"}
class NightlySettlementHealthTests(unittest.TestCase):
    def test_yesterday_all_resolved_includes_verified_voids(self):
        report=health(NOW,{},{"records":[row("SETTLED"),row("VOID_DNP")]})
        self.assertEqual(report["status"],"ALL_CAPTURED_PRIZEPICKS_RECORDS_RESOLVED")
        self.assertEqual(report["prizepicks_void"],1)
        self.assertEqual(report["prizepicks_pending"],0)

    def test_overdue_is_not_automatically_loss(self):
        report=health(NOW,{},{"records":[row()]})
        self.assertEqual(report["status"],"OVERDUE_UNRESOLVED_GRADES")
        self.assertEqual(report["prizepicks_overdue"],1)
        self.assertEqual(report["prizepicks_overdue_games"],{"Away @ Home":1})

    def test_just_finished_game_has_grace_period(self):
        report=health(NOW-dt.timedelta(hours=1),{},{"records":[row(start="2026-11-09T04:00:00Z")]})
        self.assertEqual(report["status"],"AWAITING_FINALS_OR_SETTLEMENT_GRACE_PERIOD")
        self.assertEqual(report["prizepicks_overdue"],0)

    def test_empty_captures_not_marked_complete(self):
        report=health(NOW,{},{"records":[]})
        self.assertEqual(report["status"],"NO_LOCKED_RECORDS_FOR_TARGET_DATE")
        self.assertTrue(report["capture_missing"])

    def test_future_and_other_eastern_dates_excluded(self):
        report=health(NOW,{},{"records":[row(start="2026-11-09T05:30:00Z")]})
        self.assertEqual(report["prizepicks_saved"],0)

    def test_paper_pending_is_also_overdue(self):
        p={"records":[{"status":"PENDING","event_start":DAY_START,"game":"Away @ Home"}]}
        report=health(NOW,p,{"records":[]})
        self.assertEqual(report["status"],"OVERDUE_UNRESOLVED_GRADES")
        self.assertEqual(report["paper_overdue"],1)

if __name__=="__main__":
    unittest.main()

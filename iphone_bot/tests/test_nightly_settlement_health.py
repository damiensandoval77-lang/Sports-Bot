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

    def test_prizepicks_resolved_does_not_claim_ai_forecasts_graded(self):
        ai={"game_date_eastern":"2026-11-08",
            "status":"AI_PRETIP_FORECASTS_PARTIALLY_GRADED",
            "recorded_pregame_forecasts":444,"graded":404,"ungraded":40}
        report=health(NOW,{},{"records":[row("SETTLED")]},ai_grades=ai)
        self.assertEqual(report["status"],"ALL_CAPTURED_PRIZEPICKS_RECORDS_RESOLVED")
        self.assertEqual(report["overall_grading_status"],"PRIZEPICKS_RESOLVED_AI_GRADING_INCOMPLETE")
        self.assertEqual(report["ai_forecasts_graded"],404)
        self.assertEqual(report["ai_forecasts_ungraded"],40)
        self.assertFalse(report["ai_forecasts_fully_graded"])

    def test_confirmed_ai_dnp_is_accounted_for_but_not_a_model_grade(self):
        ai={"game_date_eastern":"2026-11-08",
            "status":"AI_PRETIP_FORECASTS_GRADED",
            "recorded_pregame_forecasts":444,"graded":404,
            "verified_dnp_exclusions":40,"accounted_for":444,"ungraded":0}
        result=health(NOW,{},{"records":[row("SETTLED")]},ai_grades=ai)
        self.assertEqual(result["ai_forecasts_verified_dnp_excluded"],40)
        self.assertEqual(result["ai_forecasts_accounted_for"],444)
        self.assertTrue(result["ai_forecasts_fully_accounted_for"])
        self.assertFalse(result["ai_forecasts_fully_graded"])

    def test_wrong_day_ai_report_cannot_satisfy_nightly_grading(self):
        ai={"game_date_eastern":"2026-11-07",
            "recorded_pregame_forecasts":444,"graded":444,"ungraded":0}
        report=health(NOW,{},{"records":[row("SETTLED")]},ai_grades=ai)
        self.assertEqual(report["ai_forecast_accuracy_status"],
                         "AI_FORECAST_GRADE_REPORT_NOT_PUBLISHED_FOR_DAY")
        self.assertFalse(report["ai_forecasts_fully_graded"])

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

class NightlyReportRolloverTests(unittest.TestCase):
    def test_midnight_reads_matching_today_report_without_changing_evidence(self):
        from iphone_bot.nightly_settlement_health import select_nightly_ai_report
        now=dt.datetime(2026,11,13,5,2,tzinfo=UTC)
        reports={
            "docs/ai_forecast_grade_status.json":{"game_date_eastern":"2026-11-11","graded":808},
            "docs/ai_forecast_today_grade_status.json":{"game_date_eastern":"2026-11-12","graded":332,"ungraded":0,"verified_dnp_excluded":56}}
        selected=select_nightly_ai_report(now,lambda p:reports.get(p,{}))
        self.assertIs(selected,reports["docs/ai_forecast_today_grade_status.json"])
        self.assertEqual(selected["graded"],332)

    def test_other_dates_cannot_fill_missing_nightly_evidence(self):
        from iphone_bot.nightly_settlement_health import select_nightly_ai_report
        selected=select_nightly_ai_report(dt.datetime(2026,11,13,5,2,tzinfo=UTC),lambda p:{"game_date_eastern":"2026-11-11","graded":808})
        self.assertEqual(selected,{})

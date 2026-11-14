import copy
import datetime as dt
import json
import unittest
from pathlib import Path
from iphone_bot.audit_failure_domains import verified_posttip_slate

class FailureDomainPhaseTests(unittest.TestCase):
    def test_only_complete_fresh_verified_posttip_slate_relaxes_offer_freshness(self):
        root=Path(__file__).resolve().parents[2]/"docs"
        season=json.loads((root/"nba_season_schedule_2026_27.json").read_text())
        now=dt.datetime(2026,11,13,4,45,tzinfo=dt.timezone.utc)
        games=[g for g in season["games"] if g["date_eastern"]=="2026-11-12"]
        schedule={"coverage_complete":True,"generated_at":now.isoformat(),"games":games}
        self.assertTrue(verified_posttip_slate(schedule,season,now))
        self.assertFalse(verified_posttip_slate({**schedule,"games":games[:-1]},season,now))
        self.assertFalse(verified_posttip_slate({**schedule,"generated_at":"2026-11-12T00:00:00Z"},season,now))
        self.assertFalse(verified_posttip_slate(schedule,{},now))
        pre=now-dt.timedelta(hours=12)
        self.assertFalse(verified_posttip_slate({**schedule,"generated_at":pre.isoformat()},season,pre))
        mismatch=copy.deepcopy(schedule);mismatch["games"][0]["home_abbreviation"]="INVALID"
        self.assertFalse(verified_posttip_slate(mismatch,season,now))


class NFLStandardPendingAuditTests(unittest.TestCase):
    def checks(self, **changes):
        from unittest.mock import patch
        from iphone_bot import audit_failure_domains as audit
        original = audit.load
        report = original("nfl/data/grading_health_2026.json")
        report.update(changes)
        with patch.object(audit, "load", side_effect=lambda path: report if path == "nfl/data/grading_health_2026.json" else original(path)):
            result = audit.check_artifacts()
        return result["checks"]

    def test_alternative_pending_is_not_standard_failure(self):
        result = self.checks(pending_picks=4, standard_pending_picks=0,
                            alternative_tier_pending_excluded=4)
        self.assertFalse(any(x["code"] == "PENDING_FINAL_GRADES" for x in result))
        self.assertTrue(any(x["code"] == "STANDARD_GRADES_SETTLED" for x in result))
        self.assertTrue(any(x["code"] == "ALTERNATIVE_TIERS_EXCLUDED" and "4 pending" in x["detail"] for x in result))

    def test_actual_standard_pending_remains_visible(self):
        result = self.checks(standard_pending_picks=2)
        self.assertTrue(any(x["code"] == "PENDING_FINAL_GRADES" and "2 pending" in x["detail"] for x in result))

    def test_invalid_standard_pending_fails_closed(self):
        for value in (None, -1, "0", False):
            with self.subTest(value=value):
                result = self.checks(standard_pending_picks=value)
                self.assertTrue(any(x["code"] == "STANDARD_PENDING_COUNT_INVALID" and x["level"] == "critical" for x in result))


class NBAGradingCoverageTests(unittest.TestCase):
    def valid(self):
        return {"status": "ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR", "days": {
            "2026-11-13": {"captured": 5, "graded": 3, "void_dnp": 1,
                "excluded_nonparticipant": 1, "pending": 0, "accounted_for": 5,
                "pending_by_game": {}}}}

    def result(self, value):
        from iphone_bot.audit_failure_domains import grading_coverage_result
        return grading_coverage_result(value)

    def test_accounted_and_pending_are_distinguished(self):
        x=self.valid(); self.assertEqual(self.result(x)[0], "ok")
        x["days"]["2026-11-13"].update(captured=7,pending=2,pending_by_game={"A @ B":2})
        self.assertEqual(self.result(x)[0], "critical")
        x["status"]="VERIFIED_FINAL_ROWS_OUTSTANDING"
        self.assertEqual(self.result(x)[:2], ("warning","FINAL_ROWS_OUTSTANDING"))

    def test_unknown_missing_empty_or_contradictory_status_is_not_success(self):
        for invalid in (None, [], "OK"):
            self.assertEqual(self.result(invalid)[0],"critical")
        for status in (None,[],{},"UNKNOWN","VERIFIED_FINAL_ROWS_OUTSTANDING"):
            x=self.valid();x["status"]=status;self.assertEqual(self.result(x)[0],"critical")
        for days in (None,{},[],{"bad-date":{}}):
            x=self.valid();x["days"]=days;self.assertEqual(self.result(x)[0],"critical")

    def test_invalid_counts_or_reconciliation_fail_closed(self):
        for key in ("captured","graded","void_dnp","excluded_nonparticipant","pending","accounted_for"):
            for value in (None,-1,"0",False):
                x=self.valid();x["days"]["2026-11-13"][key]=value
                self.assertEqual(self.result(x)[0],"critical",(key,value))
        for change in ({"captured":6},{"accounted_for":4},{"pending_by_game":{"A @ B":1}},
                       {"pending_by_game":None},{"pending_by_game":{"A":False}}):
            x=self.valid();x["days"]["2026-11-13"].update(change)
            self.assertEqual(self.result(x)[0],"critical")

    def test_zero_only_report_is_not_verified_coverage(self):
        x=self.valid();row=x["days"]["2026-11-13"]
        row.update({k:0 for k in row if k!="pending_by_game"})
        self.assertEqual(self.result(x)[0],"critical")

    def test_real_published_coverage_remains_valid(self):
        root=Path(__file__).resolve().parents[2]/"docs"
        value=json.loads((root/"ai_forecast_coverage_audit.json").read_text())
        self.assertIn(self.result(value)[0],("ok","warning"))

    def test_nonobject_json_is_rejected_by_integrated_audit(self):
        from unittest.mock import patch
        from iphone_bot import audit_failure_domains as audit
        original=audit.load
        for bad in ([],None,"OK"):
            with patch.object(audit,"load",side_effect=lambda path: bad if path=="ai_forecast_coverage_audit.json" else original(path)):
                result=audit.check_artifacts()
            self.assertTrue(any(r["domain"]=="NBA grading" and r["code"]=="GRADE_AUDIT_UNAVAILABLE" and r["level"]=="critical" for r in result["checks"]))

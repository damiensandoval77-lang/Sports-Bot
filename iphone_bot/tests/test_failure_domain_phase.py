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

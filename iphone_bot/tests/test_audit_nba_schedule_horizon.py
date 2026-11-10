import datetime as dt
import unittest
from iphone_bot.audit_nba_schedule_horizon import audit
from iphone_bot.tests.test_season_schedule_baseline import baseline, NOW

class ScheduleHorizonTests(unittest.TestCase):
    def daily(self,master):
        day=NOW.date()
        dates=[(day+dt.timedelta(days=i)).isoformat() for i in (0,1)]
        rows=[{**g,"game_state":"pre"} for g in master["games"] if g["date_eastern"] in dates]
        return {"status":"THIRD_PARTY_NBA_SCHEDULE_ONLY",
                "dates_eastern":dates,"total_games":len(rows),
                "games":rows,"coverage_complete":True}

    def test_next_fourteen_dates_are_known_before_tipoff(self):
        m=baseline();report=audit(m,self.daily(m),NOW)
        self.assertEqual(report["status"],"READY")
        self.assertEqual(report["season_fixed_games"],1050)
        self.assertEqual(len(report["next_14_days"]),14)

    def test_missing_daily_game_detected_even_without_props(self):
        m=baseline();d=self.daily(m)
        d["games"]=d["games"][1:];d["total_games"]=len(d["games"])
        r=audit(m,d,NOW)
        self.assertEqual(r["status"],"DEGRADED")
        self.assertIn("PUBLISHED_GAMES_MISSING_FROM_DAILY_SLATE",r["reason_codes"])

    def test_partial_provider_never_claims_full_schedule(self):
        m=baseline();d=self.daily(m);d["coverage_complete"]=False
        r=audit(m,d,NOW)
        self.assertIn("DAILY_COVERAGE_NOT_VERIFIED",r["reason_codes"])

    def test_missing_or_corrupt_master_is_blocked(self):
        r=audit({},{"games":[]},NOW)
        self.assertEqual(r["status"],"BLOCKED")
        self.assertIn("SEASON_BASELINE_MISSING_OR_INVALID",r["reason_codes"])

    def test_duplicate_daily_identity_fails(self):
        m=baseline();d=self.daily(m)
        d["games"].append(dict(d["games"][0]))
        d["total_games"]=len(d["games"])
        r=audit(m,d,NOW)
        self.assertIn("DUPLICATE_DAILY_GAME_ID",r["reason_codes"])

if __name__=="__main__":
    unittest.main()

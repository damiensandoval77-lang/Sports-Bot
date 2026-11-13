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

class MidnightCalendarRepairTests(unittest.TestCase):
    def test_midnight_rolls_verified_fixtures_without_fabricating_props(self):
        from iphone_bot.audit_nba_schedule_horizon import repair_daily_window
        from iphone_bot.publish_nba_schedule_atomic import stage
        import datetime as dt
        master=baseline()
        before=dt.datetime(2026,11,11,4,59,tzinfo=dt.timezone.utc)
        after=dt.datetime(2026,11,11,5,1,tzinfo=dt.timezone.utc)
        daily,_=stage({},master,{},master,now=before)
        self.assertIn("DAILY_DATE_NOT_PUBLISHED",audit(master,daily,now=after)["reason_codes"])
        repaired=repair_daily_window(master,daily,now=after)
        self.assertEqual(audit(master,repaired,now=after)["status"],"READY")
        self.assertFalse(repaired["has_sportsbook_props"])
        self.assertFalse(repaired["has_verified_player_availability"])
        self.assertEqual(set(repaired["dates_eastern"]),{"2026-11-11","2026-11-12"})
        self.assertTrue(all(g.get("home_score") is None for g in repaired["games"]))

    def test_invalid_master_cannot_generate_calendar(self):
        from iphone_bot.audit_nba_schedule_horizon import repair_daily_window
        daily={"games":[],"dates_eastern":[]}
        self.assertEqual(repair_daily_window({},daily,now=NOW),daily)
        self.assertEqual(audit({},daily,now=NOW)["status"],"BLOCKED")

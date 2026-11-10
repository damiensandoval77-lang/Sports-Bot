import datetime as dt
import unittest
from iphone_bot.grading_overdue_watchdog import assess

START="2026-11-10T00:00:00+00:00"
GAME="Cleveland Cavaliers @ Charlotte Hornets"
NOW=dt.datetime.fromisoformat("2026-11-10T04:30:00+00:00")
S={"status":"THIRD_PARTY_NBA_SCHEDULE_ONLY","coverage_complete":True,
   "games":[{"game":GAME,"date_eastern":"2026-11-09","start":START}]}
P={"player_id":"123","player":"Test Player","team":"CLE","game":GAME,
   "start":START,"stat":"PTS","projection":20.1,"line":None,
   "is_pregame_prediction":True,"captured_at":"2026-11-09T23:30:00+00:00"}
A={"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE","predictions":[P]}
F={"version":1,"records":[]}

class OverdueGradeChecks(unittest.TestCase):
    def test_after_four_hours_ungraded_is_explicit_error(self):
        r=assess(S,A,F,now=NOW)
        self.assertEqual(r["status"],"OVERDUE_UNGRADED")
        self.assertEqual(r["totals"]["overdue_forecasts"],1)
        self.assertEqual(r["games"][0]["settled_verified"],0)
    def test_before_window_never_claims_failed_final_grade(self):
        r=assess(S,A,F,now=NOW-dt.timedelta(hours=1))
        self.assertEqual(r["status"],"NO_OVERDUE_PENDING")
        self.assertEqual(r["games"],[])
    def test_source_verified_grade_clears_overdue(self):
        settled={**P,"status":"GRADED","actual":19.0,"final_source":"NBA_CDN_FINAL",
                 "source_game_id":"0022600204"}
        r=assess(S,A,{"version":1,"records":[settled]},now=NOW)
        self.assertEqual(r["status"],"NO_OVERDUE_PENDING")
        self.assertEqual(r["totals"]["settled_forecasts"],1)
    def test_live_prediction_or_no_final_source_cannot_clear(self):
        bogus={**P,"status":"GRADED","actual":19,"final_source":"LIVE_ESPN"}
        r=assess(S,A,{"version":1,"records":[bogus]},now=NOW)
        self.assertEqual(r["status"],"OVERDUE_UNGRADED")
    def test_missing_schedule_or_missing_archive_causes_visible_failure(self):
        self.assertEqual(assess({**S,"coverage_complete":False},A,F,NOW)["status"],
                         "OVERDUE_MONITOR_SOURCE_ERROR")
        self.assertEqual(assess(S,{},F,NOW)["status"],"OVERDUE_MONITOR_SOURCE_ERROR")

if __name__=="__main__":unittest.main()

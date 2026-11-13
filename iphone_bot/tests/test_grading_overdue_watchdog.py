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
    def test_rolling_schedule_can_advance_but_season_preserves_nov10_overdue(self):
        now=dt.datetime.fromisoformat("2026-11-11T09:28:00+00:00")
        game={"game":"Milwaukee Bucks @ New York Knicks",
              "date_eastern":"2026-11-10","start":"2026-11-11T00:30:00+00:00"}
        upcoming={"game":"Brooklyn Nets @ New Orleans Pelicans",
                 "date_eastern":"2026-11-11","start":"2026-11-12T01:00:00+00:00"}
        rolled={**S,"games":[upcoming]}
        self.assertEqual(assess(rolled,A,F,now)["status"],"NO_OVERDUE_PENDING")
        season={"status":"VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE",
                "season":"2026-27",
                "coverage":"PUBLISHED_FIXED_REGULAR_SEASON_GAMES_ONLY",
                "total_games":1200,"games":[game]+[upcoming]*1199}
        frozen={**P,"game":game["game"],"team":"MIL",
                "start":game["start"],
                "captured_at":"2026-11-10T23:00:00+00:00"}
        source={**A,"predictions":[frozen]}
        r=assess(season,source,F,now)
        self.assertEqual(r["status"],"OVERDUE_UNGRADED")
        self.assertEqual(r["totals"]["overdue_forecasts"],1)
        self.assertEqual(r["schedule_source"],"VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE")
        settled={**frozen,"status":"GRADED","actual":10,
                 "final_source":"NBA_CDN_FINAL","source_game_id":"0022600211"}
        clean=assess(season,source,{"version":1,"records":[settled]},now)
        self.assertEqual(clean["status"],"NO_OVERDUE_PENDING")
        self.assertEqual(clean["totals"]["settled_forecasts"],1)

    def test_unverified_partial_season_schedule_fails_closed(self):
        season={"status":"VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE",
                "season":"2026-27","coverage":"PUBLISHED_FIXED_REGULAR_SEASON_GAMES_ONLY",
                "total_games":1200,"games":[S["games"][0]]}
        self.assertEqual(assess(season,A,F,now=NOW)["status"],
                         "OVERDUE_MONITOR_SOURCE_ERROR")

    def test_archived_unsettled_forecast_never_ages_out_at_48_hours(self):
        five_days_later=NOW+dt.timedelta(days=5)
        ungraded=assess(S,A,F,now=five_days_later)
        self.assertEqual(ungraded["status"],"OVERDUE_UNGRADED")
        self.assertEqual(ungraded["totals"]["scanned_game_count"],1)
        self.assertEqual(ungraded["totals"]["overdue_game_count"],1)
        self.assertEqual(ungraded["totals"]["overdue_forecasts"],1)
        verified={**P,"status":"GRADED","actual":19,
                  "final_source":"NBA_CDN_FINAL","source_game_id":"0022600204"}
        completed=assess(S,A,{"records":[verified]},now=five_days_later)
        self.assertEqual(completed["status"],"NO_OVERDUE_PENDING")
        self.assertEqual(completed["totals"]["overdue_game_count"],0)

    def test_scanned_games_are_not_mislabeled_all_overdue(self):
        second={"game":"New York Knicks @ Boston Celtics",
                "date_eastern":"2026-11-09","start":START}
        schedule={**S,"games":[S["games"][0],second]}
        archived={**A,"predictions":[P,{**P,"game":second["game"],"player_id":"456"}]}
        verified={**P,"status":"GRADED","actual":19,
                  "final_source":"NBA_CDN_FINAL","source_game_id":"0022600204"}
        status=assess(schedule,archived,{"records":[verified]},now=NOW)
        self.assertEqual(status["totals"]["scanned_game_count"],2)
        self.assertEqual(status["totals"]["overdue_game_count"],1)
        self.assertEqual(status["totals"]["overdue_forecasts"],1)

    def test_missing_schedule_or_missing_archive_causes_visible_failure(self):
        self.assertEqual(assess({**S,"coverage_complete":False},A,F,NOW)["status"],
                         "OVERDUE_MONITOR_SOURCE_ERROR")
        self.assertEqual(assess(S,{},F,NOW)["status"],"OVERDUE_MONITOR_SOURCE_ERROR")

    def test_future_capture_does_not_include_old_meeting_of_same_teams(self):
        old={**S['games'][0],'start':'2026-10-24T00:00:00+00:00',
             'date_eastern':'2026-10-23'}
        future={**P,'start':'2026-11-14T00:00:00+00:00',
                'captured_at':'2026-11-13T12:00:00+00:00'}
        result=assess({**S,'games':[old]}, {**A,'predictions':[future]},F,NOW)
        self.assertEqual(result['games'],[])
        self.assertEqual(result['status'],'NO_OVERDUE_PENDING')

    def test_repeated_matchups_preserve_each_archived_meeting(self):
        old={**S['games'][0],'start':'2026-10-24T00:00:00+00:00',
             'date_eastern':'2026-10-23'}
        prior={**P,'start':old['start'],'captured_at':'2026-10-23T23:30:00+00:00'}
        settled={**P,'status':'GRADED','actual':19,'final_source':'NBA_CDN_FINAL',
                 'source_game_id':'0022600204'}
        for games in ([old,S['games'][0]],[S['games'][0],old]):
            result=assess({**S,'games':games},{**A,'predictions':[prior,P]},
                          {'records':[settled]},NOW)
            self.assertEqual(result['totals']['scanned_game_count'],2)
            self.assertEqual(result['totals']['overdue_forecasts'],1)
            self.assertEqual(result['totals']['settled_forecasts'],1)
            self.assertEqual(result['games'][0]['start'],old['start'])
            self.assertEqual(result['games'][0]['status'],'OVERDUE_UNGRADED')

    def test_equivalent_timezone_and_small_tip_shift_match(self):
        shifted={**S['games'][0],'start':'2026-11-09T19:10:00-05:00'}
        result=assess({**S,'games':[shifted]},A,F,NOW)
        self.assertEqual(result['totals']['overdue_forecasts'],1)

if __name__=="__main__":unittest.main()

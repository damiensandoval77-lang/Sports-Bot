import datetime as dt
import unittest
from iphone_bot.pregame_coverage_watchdog import check

NOW=dt.datetime(2026,11,9,23,40,tzinfo=dt.timezone.utc)
START="2026-11-10T00:00:00+00:00"
GAME="Cleveland Cavaliers @ Charlotte Hornets"
SCHEDULE={"coverage_complete":True,
 "official_fixture_reconciliation":{"verified_daily_counts":{"2026-11-09":{"complete":True}}},
 "games":[{"game":GAME,"date_eastern":"2026-11-09","start":START}]}
PRED={"game":GAME,"start":START,"player":"Test","player_id":"1","is_pregame_prediction":True,"line":None,"direction":None}
FORECAST={"predictions":[PRED]}
ARCHIVE={"predictions":[{**PRED,"captured_at":"2026-11-09T23:31:00+00:00"}]}
QUICK={"matched_by_game":{GAME:17},"partial_provider_board":True}

class CoverageWatchdogTests(unittest.TestCase):
    def test_source_publications_trigger_coverage_check(self):
        from pathlib import Path
        workflow=Path(".github/workflows/pregame_coverage_watchdog.yml").read_text()
        self.assertIn("  push:",workflow)
        for input_file in (
            "docs/nba_schedule.json",
            "docs/ai_projection_fallback.json",
            "docs/ai_no_line_pregame_archive.json",
            "docs/ai_prizepicks_quick_join_health.json",
        ):
            self.assertIn(input_file,workflow)
        self.assertNotIn("'docs/pregame_coverage_watchdog.json'",workflow)

    def test_all_eight_style_coverage_counts_are_explicit(self):
        r=check(NOW,SCHEDULE,FORECAST,ARCHIVE,QUICK)
        self.assertEqual(r["status"],"COVERED")
        self.assertEqual(r["games_with_frozen_forecasts"],1)
        self.assertEqual(r["games_with_published_comparisons"],1)
        self.assertTrue(r["provider_board_partial"])

    def test_missing_immutable_capture_imminent_tipoff_is_critical(self):
        r=check(NOW,SCHEDULE,FORECAST,{},QUICK)
        self.assertEqual(r["status"],"AT_RISK")
        self.assertIn(GAME,r["critical_games"])
        self.assertIn("IMMINENT_TIPOFF_WITHOUT_FROZEN_AI",r["games"][0]["reasons"])

    def test_late_capture_cannot_count_as_pretip(self):
        archive={"predictions":[{**PRED,"captured_at":"2026-11-10T00:01:00Z"}]}
        self.assertEqual(check(NOW,SCHEDULE,FORECAST,archive,QUICK)["status"],"AT_RISK")

    def test_missing_compared_lines_watch_not_fabrication(self):
        r=check(NOW,SCHEDULE,FORECAST,ARCHIVE,{"matched_by_game":{},"partial_provider_board":True})
        self.assertEqual(r["status"],"AT_RISK")
        self.assertEqual(r["games"][0]["published_prizepicks_matches"],0)
        self.assertIn("NO_PUBLISHED_PRIZEPICKS_AI_COMPARISON",r["games"][0]["reasons"])

    def test_hours_before_tipoff_missing_frozen_snapshot_is_watch(self):
        early=NOW-dt.timedelta(hours=2)
        r=check(early,SCHEDULE,FORECAST,{},QUICK)
        self.assertEqual(r["status"],"MONITORING")
        self.assertFalse(r["critical_games"])

    def test_after_tipoff_missing_capture_is_critical(self):
        later=NOW+dt.timedelta(hours=1)
        r=check(later,SCHEDULE,FORECAST,{},QUICK)
        self.assertEqual(r["status"],"AT_RISK")
        self.assertIn("TIPOFF_WITHOUT_FROZEN_AI",r["games"][0]["reasons"])

if __name__=="__main__":unittest.main()

"""Pure offline contract tests for the eight-game readiness audit."""
import datetime as dt
import unittest
from iphone_bot.end_to_end_readiness import evaluate

NOW = dt.datetime(2026, 11, 9, 17, 30, tzinfo=dt.timezone.utc)
GAME = "Washington Wizards @ Detroit Pistons"

def fixtures():
    t = "2026-11-09T17:25:00+00:00"
    slate = {"generated_at": t, "games":[{"game":GAME,"date_eastern":"2026-11-09"}],
             "official_fixture_reconciliation":{"verified_daily_counts":{
                 "2026-11-09":{"complete":True,"official_expected":1}}}}
    health = {"generated_at":t,"provider_generated_at":t,"model_generated_at":t,
              "status":"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
              "matched_by_game":{GAME:10,"Tomorrow @ Team":5},
              "partial_provider_board":False,"source_coverage_complete":True,
              "research_only":True}
    production = {"checked_at":t,"game_date_eastern":"2026-11-09",
                  "ready_for_trustworthy_picks":True}
    grades = {"generated_at":t,"game_date_eastern":"2026-11-08",
              "ungraded":0,"recorded_pregame_forecasts":10}
    return slate, health, production, grades

class ReadinessTests(unittest.TestCase):
    def test_healthy_snapshot(self):
        result = evaluate(*fixtures(), now=NOW)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["matched_offers_today"], 10)
        self.assertEqual(result["other_day_game_labels"], ["Tomorrow @ Team"])
    def test_missing_eighth_game_match_is_not_ready(self):
        a = fixtures()
        a[0]["games"].append({"game":"Second @ Game","date_eastern":"2026-11-09"})
        a[0]["official_fixture_reconciliation"]["verified_daily_counts"]["2026-11-09"]["official_expected"]=2
        self.assertIn("GAMES_WITHOUT_VERIFIED_COMPARISONS", evaluate(*a, now=NOW)["failures"])
    def test_partial_feed_is_not_ready_even_with_many_matches(self):
        a = fixtures()
        a[1]["partial_provider_board"]=True
        self.assertIn("PARTIAL_PRIZEPICKS_BOARD",evaluate(*a,now=NOW)["failures"])
    def test_stale_data_and_missing_grades_fail(self):
        a=fixtures()
        a[1]["provider_generated_at"]="2026-11-09T12:00:00+00:00"
        a[3]["ungraded"]=24
        failures=evaluate(*a,now=NOW)["failures"]
        self.assertIn("STALE_PRIZEPICKS_SOURCE",failures)
        self.assertIn("PREVIOUS_DAY_FORECASTS_UNGRADED",failures)
    def test_missing_schedule_fails_closed(self):
        self.assertIn("INCOMPLETE_VERIFIED_SLATE",evaluate({}, {}, {}, {}, now=NOW)["failures"])

if __name__ == "__main__":
    unittest.main()

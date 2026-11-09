"""Deterministic offline checks for public Chromium full-slate readiness."""
import datetime as dt
import unittest
from pathlib import Path
from iphone_bot.verify_browser_dashboard import assess,EXPECTED

NOW=dt.datetime(2026,11,9,19,20,tzinfo=dt.timezone.utc)
COUNTS={g:1 for g in EXPECTED}

class BrowserCardProbeTests(unittest.TestCase):
    def test_eight_games_have_standard_lines_plus_some_new_model(self):
        report=assess(204,["Standard line"],list(EXPECTED),[],NOW,
                      COUNTS,modeled_count=47,line_only_count=157)
        self.assertEqual(report["status"],"READY")
        self.assertTrue(report["browser_render_verified"])
        self.assertTrue(report["new_ai_model_coverage_partial"])
        self.assertEqual(report["missing_official_games"],[])

    def test_all_lines_but_no_new_ai_is_degraded(self):
        output=assess(204,["Line"],list(EXPECTED),[],NOW,COUNTS,
                      modeled_count=0,line_only_count=204)
        self.assertEqual(output["status"],"DEGRADED")
        self.assertIn("NEW_AI_MODEL_CARDS_NOT_RENDERED",output["reasons"])

    def test_zero_cards_is_not_ready(self):
        report=assess(0,[],list(EXPECTED),[],NOW,COUNTS)
        self.assertEqual(report["status"],"DEGRADED")
        self.assertIn("NO_RENDERED_NBA_MARKET_CARDS",report["reasons"])

    def test_no_standard_line_still_fails_even_with_ai_cards(self):
        report=assess(50,[],list(EXPECTED),[],NOW,COUNTS,modeled_count=50)
        self.assertIn("NO_RENDERED_STANDARD_PRIZEPICKS_LINES",report["reasons"])

    def test_one_missing_upcoming_game_is_degraded(self):
        counts=dict(COUNTS)
        game=sorted(EXPECTED)[0]
        counts[game]=0
        r=assess(204,["Line"],list(EXPECTED),[],NOW,counts,modeled_count=47)
        self.assertEqual(r["status"],"DEGRADED")
        self.assertEqual(r["games_without_rendered_matches"],[game])

    def test_started_game_does_not_require_live_pregame_market(self):
        remaining=set(EXPECTED)-{sorted(EXPECTED)[0]}
        r=assess(185,["Line"],list(EXPECTED),[],NOW,
                 {k:1 for k in remaining},modeled_count=22,expected_games=remaining)
        self.assertEqual(r["status"],"READY")

    def test_no_upcoming_games_is_not_false_outage(self):
        r=assess(0,[],list(EXPECTED),[],NOW,{},expected_games=set())
        self.assertEqual(r["status"],"NO_UPCOMING_GAMES")

    def test_workflow_monitors_main_page_and_new_model_source(self):
        workflow=Path(".github/workflows/verify_browser_dashboard.yml").read_text()
        self.assertIn("docs/index.html",workflow)
        self.assertIn("python -m iphone_bot.verify_browser_dashboard",workflow)
        self.assertNotIn("PRIZEPICKS_API_KEY",workflow)

if __name__=="__main__":unittest.main()

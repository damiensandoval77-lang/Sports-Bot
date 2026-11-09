"""Offline contract for the actual public Chromium iPhone dashboard canary."""
import datetime as dt
import unittest
from pathlib import Path
from iphone_bot.verify_browser_dashboard import assess,EXPECTED

NOW=dt.datetime(2026,11,9,19,20,tzinfo=dt.timezone.utc)

class BrowserCardProbeTests(unittest.TestCase):
    def test_renders_real_prizepicks_and_ai_metrics_for_full_eight_game_slate(self):
        report=assess(120,["Game card verified"],list(EXPECTED),[],NOW)
        self.assertEqual(report["status"],"READY")
        self.assertTrue(report["browser_render_verified"])
        self.assertEqual(report["missing_official_games"],[])

    def test_no_cards_is_not_equivalent_to_loading_page(self):
        report=assess(0,[],list(EXPECTED),[],NOW)
        self.assertEqual(report["status"],"DEGRADED")
        self.assertIn("NO_RENDERED_PRIZEPICKS_AI_CARDS",report["reasons"])

    def test_no_genuine_prizepicks_line_must_fail(self):
        report=assess(120,[],list(EXPECTED),[],NOW)
        self.assertIn("NO_RENDERED_LINE_AND_PROJECTION_VALUES",report["reasons"])

    def test_missing_even_one_game_tile_fails(self):
        report=assess(120,["Card"],list(EXPECTED)[:-1],[],NOW)
        self.assertEqual(len(report["missing_official_games"]),1)

    def test_workflow_runs_after_provider_join_publication(self):
        workflow=Path(".github/workflows/verify_browser_dashboard.yml").read_text()
        self.assertIn("docs/ai_prizepicks_quick_join_health.json",workflow)
        self.assertIn("python -m iphone_bot.verify_browser_dashboard",workflow)
        self.assertNotIn("PRIZEPICKS_API_KEY",workflow)

if __name__=="__main__":
    unittest.main()

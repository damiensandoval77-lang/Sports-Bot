"""Offline contract for the actual public Chromium iPhone dashboard canary."""
import datetime as dt
import unittest
from pathlib import Path
from iphone_bot.verify_browser_dashboard import assess,EXPECTED

NOW=dt.datetime(2026,11,9,19,20,tzinfo=dt.timezone.utc)

class BrowserCardProbeTests(unittest.TestCase):
    def test_rendered_cards_cannot_mask_browser_exception(self):
        report=assess(120,["Actual card"],list(EXPECTED),["ReferenceError"],NOW,
                      {g:1 for g in EXPECTED},standard_lines=120,model_chances=120)
        self.assertEqual(report["status"],"DEGRADED")
        self.assertIn("UNHANDLED_JS_ERRORS",report["reasons"])

    def test_renders_real_prizepicks_and_ai_metrics_for_full_eight_game_slate(self):
        report=assess(120,["Game card verified"],list(EXPECTED),[],NOW,
                      {g:1 for g in EXPECTED},standard_lines=120,model_chances=30)
        self.assertEqual(report["status"],"READY")
        self.assertTrue(report["browser_render_verified"])
        self.assertEqual(report["missing_official_games"],[])

    def test_visible_authenticated_lines_but_no_new_ai_chances_fails(self):
        counts={game:1 for game in EXPECTED}
        bad=assess(300,["Real PP line"],list(EXPECTED),[],NOW,counts,standard_lines=300,model_chances=0)
        self.assertEqual(bad["status"],"DEGRADED")
        self.assertIn("NO_RENDERED_NEW_AI_CHANCES",bad["reasons"])
        good=assess(300,["Real PP line"],list(EXPECTED),[],NOW,counts,standard_lines=300,model_chances=20)
        self.assertEqual(good["status"],"READY")
        self.assertEqual(good["rendered_new_ai_chances"],20)

    def test_no_cards_is_not_equivalent_to_loading_page(self):
        report=assess(0,[],list(EXPECTED),[],NOW)
        self.assertEqual(report["status"],"DEGRADED")
        self.assertIn("NO_RENDERED_PRIZEPICKS_AI_CARDS",report["reasons"])

    def test_no_genuine_prizepicks_line_must_fail(self):
        report=assess(120,[],list(EXPECTED),[],NOW)
        self.assertIn("NO_RENDERED_VERIFIED_STANDARD_LINES",report["reasons"])

    def test_each_game_must_actually_render_its_own_line_and_ai_cards(self):
        counts={game:1 for game in EXPECTED}
        good=assess(120,["Card"],list(EXPECTED),[],NOW,counts,standard_lines=120,model_chances=20)
        self.assertEqual(good["status"],"READY")
        game=sorted(EXPECTED)[0]
        counts[game]=0
        bad=assess(120,["Card"],list(EXPECTED),[],NOW,counts)
        self.assertEqual(bad["status"],"DEGRADED")
        self.assertEqual(bad["games_without_rendered_matches"],[game])
        self.assertIn("SCHEDULED_GAME_WITHOUT_RENDERED_PP_AI_CARDS",bad["reasons"])

    def test_missing_even_one_game_tile_fails(self):
        report=assess(120,["Card"],list(EXPECTED)[:-1],[],NOW)
        self.assertEqual(len(report["missing_official_games"]),1)

    def test_started_games_keep_navigation_but_do_not_require_pregame_cards(self):
        all_games=set(EXPECTED)
        still_pretip=set(sorted(EXPECTED)[-3:])
        counts={g:1 for g in still_pretip}
        report=assess(65,["Real standard quote"],list(all_games),[],NOW,counts,
                      standard_lines=65,model_chances=15,
                      expected_games=all_games,required_upcoming=still_pretip)
        self.assertEqual(report["status"],"READY")
        self.assertEqual(report["scheduled_game_count"],8)
        self.assertEqual(report["upcoming_game_count"],3)
        self.assertEqual(report["games_without_rendered_matches"],[])

    def test_missing_upcoming_game_still_fails(self):
        all_games=set(EXPECTED)
        still_pretip=set(sorted(EXPECTED)[-2:])
        missing=sorted(still_pretip)[0]
        report=assess(20,["Line"],list(all_games),[],NOW,
                      {missing:0,sorted(still_pretip)[1]:2},standard_lines=20,
                      model_chances=4,expected_games=all_games,
                      required_upcoming=still_pretip)
        self.assertEqual(report["status"],"DEGRADED")
        self.assertEqual(report["games_without_rendered_matches"],[missing])

    def test_no_pregame_cards_expected_after_every_game_tips(self):
        report=assess(0,[],list(EXPECTED),[],NOW,{},standard_lines=0,
                      model_chances=0,expected_games=EXPECTED,required_upcoming=set())
        self.assertEqual(report["status"],"READY")
        self.assertEqual(report["upcoming_game_count"],0)

    def test_workflow_runs_after_provider_join_publication(self):
        workflow=Path(".github/workflows/verify_browser_dashboard.yml").read_text()
        self.assertIn("docs/ai_prizepicks_quick_join_health.json",workflow)
        self.assertIn("python -m iphone_bot.verify_browser_dashboard",workflow)
        self.assertNotIn("PRIZEPICKS_API_KEY",workflow)

if __name__=="__main__":
    unittest.main()

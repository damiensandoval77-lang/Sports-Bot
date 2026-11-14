import ast
from pathlib import Path
import unittest
from scripts.mobile_card_scope import BOARD_CARDS, BOARD_GAMES

class CardScopeTests(unittest.TestCase):
    def test_selectors_exclude_retained_detail_and_hidden_board(self):
        self.assertEqual(BOARD_CARDS, '#board:not(.hidden) #cards button.pick')
        self.assertEqual(BOARD_GAMES, '#board:not(.hidden) #cards [data-game]')

    def test_every_canary_pick_and_game_locator_is_scoped(self):
        src=(Path(__file__).parents[1]/'scripts/e2e_live_site.py').read_text()
        ast.parse(src)
        self.assertNotIn("locator('button.pick')",src)
        self.assertNotIn('locator("button.pick")',src)
        self.assertNotIn("locator('[data-game]')",src)
        self.assertNotIn("querySelectorAll('button.pick')",src)
        self.assertIn('page.locator(BOARD_CARDS).first.wait_for(timeout=15000)',src)
        self.assertIn('page.locator(BOARD_CARDS).first.click()',src)
        self.assertIn('verify_board_scope(browser)',src)
        self.assertIn('check(sport.lower()+"_player_detail_and_take",False',src)

    def test_isolated_browser_probe_always_closes_fixture(self):
        from unittest.mock import Mock
        from scripts.mobile_card_scope import verify_board_scope
        browser=Mock();page=browser.new_page.return_value
        cards=Mock();games=Mock()
        page.locator.side_effect=lambda selector: cards if selector==BOARD_CARDS else games if selector==BOARD_GAMES else Mock()
        cards.count.side_effect=[1,0];games.count.side_effect=[1,0]
        cards.first.get_attribute.return_value='yes'
        self.assertTrue(verify_board_scope(browser));page.close.assert_called_once()
        cards.first.click.assert_called_once()

    def test_failed_probe_still_closes(self):
        from unittest.mock import Mock
        from scripts.mobile_card_scope import verify_board_scope
        browser=Mock();page=browser.new_page.return_value
        page.locator.return_value.count.return_value=2
        self.assertFalse(verify_board_scope(browser));page.close.assert_called_once()

class BrowserCardScopeTests(unittest.TestCase):
    @unittest.skipUnless(__import__('os').environ.get('DAMES_SCOPE_BROWSER_TEST')=='1', 'browser regression runs in configured CI')
    def test_actual_browser_ignores_hidden_previous_sport_detail(self):
        from playwright.sync_api import sync_playwright
        from scripts.mobile_card_scope import verify_board_scope
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                self.assertTrue(verify_board_scope(browser))
            finally:
                browser.close()

class BrowserMarketTabTests(unittest.TestCase):
    @unittest.skipUnless(__import__('os').environ.get('DAMES_SCOPE_BROWSER_TEST')=='1', 'browser regression runs in configured CI')
    def test_long_market_names_fit_production_tab_buttons(self):
        import re
        from playwright.sync_api import sync_playwright
        html=(Path(__file__).parents[1]/'docs/dames-picks/index.html').read_text()
        css=re.search(r'<style>(.*?)</style>',html,re.S).group(1)
        labels=['Fantasy Score · 15.0','Pass Attempts · 29.5','Pass Completions · 18.0','INT · 0.5','Pass+Rush Yds · 225.5']
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                page=browser.new_page(viewport={'width':390,'height':844})
                page.set_content('<style>'+css+'</style><div class="app"><div class="tabstrip">'+''.join('<button>'+label+'</button>' for label in labels)+'</div></div>')
                self.assertEqual(page.locator('button').count(),len(labels))
                self.assertTrue(page.locator('button').evaluate_all('bs => bs.every(b => b.scrollWidth <= b.clientWidth + 1)'))
                self.assertTrue(page.locator('.tabstrip').evaluate('b => b.scrollWidth > b.clientWidth'))
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                page.locator('button').last.scroll_into_view_if_needed()
                self.assertTrue(page.locator('button').last.is_visible())
            finally:
                browser.close()

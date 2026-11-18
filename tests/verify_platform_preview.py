"""Local UI checks only. Does not certify GitHub Pages, real iOS, or sports feeds.
Usage: python tests/verify_platform_preview.py [--browser /usr/bin/chromium]
Requires playwright and a browser; no provider credentials or network needed.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / 'docs/dames-picks/platform-preview.html'
ROUTES = ('overview', 'sports', 'players', 'ai', 'lab')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', help='Optional Chromium executable path')
    parser.add_argument('--artifacts', type=Path, default=ROOT / 'test-artifacts')
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    html = HTML.read_text(encoding='utf-8')
    report = {'scope': 'local Chromium only; NOT production or real iPhone verification', 'checks': []}
    with sync_playwright() as p:
        options = {'headless': True}
        if args.browser:
            options['executable_path'] = args.browser
        browser = p.chromium.launch(**options)
        for width, height in ((320, 740), (393, 852), (768, 1024), (1440, 1120)):
            page = browser.new_page(viewport={'width': width, 'height': height})
            errors, requests = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: requests.append(r.url))
            page.set_content(html, wait_until='load')
            for route in ROUTES:
                page.evaluate('(route) => { location.hash = route; }', route)
                page.wait_for_function('(route) => !document.querySelector("#view-" + route).hidden', arg=route)
                assert page.locator('[data-page]:visible').count() == 1
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), (width, route)
                assert page.locator(f'[data-route="{route}"][aria-current="page"]').count() == 2
                report['checks'].append(f'{width}px/{route}: visible route, active navigation, no horizontal overflow')
            for league in ('NFL', 'Tennis', 'NBA'):
                page.locator(f'[data-league="{league}"]').click()
                assert page.locator('#scope').inner_text() == league + ' workspace'
            page.evaluate("location.hash='sports'")
            page.locator('#game-status').select_option('Live')
            assert 'live' in page.locator('#sports-empty-copy').inner_text()
            page.locator('[data-tabgroup="sports"] [data-value="Injuries"]').click()
            assert page.locator('#sports-empty-title').inner_text() == 'Injury feed not connected'
            page.evaluate("location.hash='players'")
            hostile = '<img src=x onerror=window.__unsafe=true>'
            page.locator('#player-query').fill(hostile)
            page.locator('#player-search button').click()
            assert hostile in page.locator('#search-result').inner_text()
            assert page.locator('#search-result img').count() == 0
            assert page.evaluate('window.__unsafe === undefined')
            page.locator('[data-tabgroup="history"] [data-value="L15"]').click()
            assert 'Last 15 games' in page.locator('#history-notice').inner_text()
            page.evaluate("location.hash='ai'")
            first_prompt = page.locator('.prompt-button').first
            first_prompt.click()
            assert page.locator('#ai-question').input_value() == first_prompt.inner_text()
            assert page.locator('.composer button').is_disabled()
            page.evaluate("location.hash='lab'")
            page.locator('[data-tabgroup="lab"] [data-value="Under"]').click()
            assert page.locator('#lab-notice').inner_text().startswith('Under directions selected')
            page.evaluate("location.hash='not-a-valid-route'")
            page.wait_for_function("!document.querySelector('#view-overview').hidden")
            assert not errors, errors
            assert not requests, requests
            report['checks'].append(f'{width}px: sports, filters, search injection, AI disabled, unknown-route fallback, zero network, zero JS errors')
            page.screenshot(path=str(args.artifacts / f'overview-{width}.png'), full_page=True)
            if width == 393:
                page.screenshot(path=str(args.artifacts / 'mobile-viewport.png'), full_page=False)
            page.close()
        browser.close()
    report['status'] = 'PASS'
    report['check_groups'] = len(report['checks'])
    (args.artifacts / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()

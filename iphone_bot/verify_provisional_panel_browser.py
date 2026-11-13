"""Local 390px browser regression using explicitly synthetic test-only input.

No production/provider calls; this is not a live deployment verification.
"""
import datetime as dt
import functools
import http.server
import json
from pathlib import Path
import threading
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]/'docs'

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass


def fixture():
    now=dt.datetime.now(dt.timezone.utc)
    # Use three minutes for slow CI, bounded to the same Eastern schedule day.
    eastern=now.astimezone(ZoneInfo('America/New_York'))
    end=eastern.replace(hour=23,minute=59,second=59,microsecond=999999).astimezone(dt.timezone.utc)
    tip=min(now+dt.timedelta(minutes=3),end)
    day=tip.astimezone(ZoneInfo('America/New_York')).date()
    dates=[(day-dt.timedelta(days=n)).isoformat() for n in (6,4,2)]
    row=dict(player='Regression Fixture',player_id='fixture-only',team='MEM',opponent='DAL',
        game='Memphis @ Dallas',start=tip.isoformat(),stat='PTS',line=12.5,projection=11.125,
        captured_at=now.isoformat(),market_updated=(now-dt.timedelta(minutes=1)).isoformat(),
        prior_games=3,history_dates=dates,method='ARITHMETIC_MEAN_PRIOR_SAME_TEAM_GAMES',
        label='Provisional estimate',cohort='PROVISIONAL_SHORT_HISTORY',research_only=True,trained_model=False,
        primary_model_eligible=False,official_grade_eligible=False,estimated_hit_chance=None,
        calibrated_probability=None,hit_probability=None,injury_context_status='NO_REPORTED_OUT',
        source='INDEPENDENTLY_CROSSCHECKED_PLAYER_HISTORY',pickem_tier='standard',standard_line_two_sided_verified=True)
    return dict(status='PROVISIONAL_SHORT_HISTORY_DESCRIPTIVE_BASELINE',generated_at=now.isoformat(),
        official_report_issued_at=(now-dt.timedelta(minutes=5)).isoformat(),
        cohort='PROVISIONAL_SHORT_HISTORY',trained_model=False,primary_model_eligible=False,
        official_grade_eligible=False,performance_metrics=None,estimates=[row],count=1)


def check():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    errors=[];unavailable=[False]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                def route(request):
                    url=request.request.url
                    if not url.startswith(base):request.abort();return
                    if '/provisional_short_history.json' in url:
                        request.fulfill(status=503 if unavailable[0] else 200,
                            content_type='application/json',body=json.dumps({} if unavailable[0] else fixture()))
                        return
                    request.continue_()
                page.route('**/*',route)
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(base+'/dames-picks/',wait_until='domcontentloaded')
                page.wait_for_function('() => !state.loading && !!state.updated')
                panel=page.locator('#provisional-short-history')
                assert panel.is_visible()
                assert not panel.locator('details').evaluate('(x)=>x.open')
                panel.locator('summary').click()
                assert panel.get_by_text('Regression Fixture · PTS',exact=True).is_visible()
                assert panel.locator('button,[data-id],a').count()==0
                assert 'not trained AI picks' in panel.inner_text()
                assert 'Ungraded' in panel.inner_text()
                assert not page.evaluate("state.nba.some(x=>x.player==='Regression Fixture')")
                assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth+2')
                assert not page.locator('#diagnostics').is_visible()
                for mode in ('tracker','saved','live'):
                    page.locator(f'[data-view="{mode}"]').click()
                    assert not panel.is_visible(), mode
                page.locator('[data-view="board"]').click()
                page.locator('[data-league="NFL"]').click()
                assert not panel.is_visible()
                page.locator('[data-league="NBA"]').click()
                assert panel.is_visible()
                panel.locator('summary').click()
                page.locator('#query').fill('no matching fixture')
                assert 'No provisional estimates match' in panel.inner_text()
                page.locator('#query').fill('')
                before=page.evaluate("({count:state.nba.length,wl:document.querySelector('#wl').textContent,rate:document.querySelector('#rate').textContent})")
                unavailable[0]=True
                page.locator('#refresh').click()
                page.wait_for_function('() => !state.loading && state.provisionalFeed===null')
                assert 'Provisional estimates unavailable' in panel.inner_text()
                after=page.evaluate("({count:state.nba.length,wl:document.querySelector('#wl').textContent,rate:document.querySelector('#rate').textContent})")
                assert before==after, 'Optional unavailable panel changed primary counts/statistics'
                assert not errors, errors
                print('PASS: local Chromium 390px provisional fixture, disclosure/search/navigation/unavailable refresh, primary isolation, no overflow or JS errors. NOT live verification.')
            finally:browser.close()
    finally:server.shutdown();server.server_close()

if __name__=='__main__':check()

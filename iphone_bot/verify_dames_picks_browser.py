"""Actual Chromium smoke test of Version E against saved repository feeds, no paid provider calls."""
from __future__ import annotations
import contextlib
import functools
import http.server
import pathlib
import threading
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]/"docs"

def check():
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT))
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
    runner=threading.Thread(target=server.serve_forever,daemon=True)
    runner.start()
    url=f"http://127.0.0.1:{server.server_port}/dames-picks/"
    errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            try:
                page=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=2)
                page.on("pageerror",lambda e:errors.append(str(e)))
                response=page.goto(url,wait_until="domcontentloaded",timeout=45000)
                assert response and response.status==200, "Version E HTTP 200 missing"
                page.wait_for_function("() => document.querySelector('#status').textContent.includes('Checked')",timeout=30000)
                page.locator('[data-view="tracker"]').click()
                try:
                    page.locator(".pick").first.wait_for(timeout=15000)
                except Exception:
                    details=page.evaluate("""() => ({
                        status:document.querySelector('#status')?.textContent,
                        view:state.mode,
                        now:new Date().toISOString(),
                        nowEastern:new Date().toLocaleString('en-US',{timeZone:'America/New_York'}),
                        nbaCount:state.nba.length,
                        sample:state.nba.slice(0,3).map(p=>({player:p.player,start:p.start,captured:p.captured,stat:p.stat})),
                        currentCount:m.displayCurrentPicks(state.nba,Date.now(),true).length
                    })""")
                    raise AssertionError(f"NBA tracker rendered zero current slate cards: {details}; page errors={errors[:5]}")
                nba_count=page.locator(".pick").count()
                assert nba_count>0,"No NBA tracker cards from published frozen ledger"
                page.locator(".pick").first.click()
                page.locator("#detail:not(.hidden)").wait_for()
                assert page.locator("#detail-content .hero").count()==1,"NBA player detail did not render"
                page.locator("#back").click()
                page.locator('[data-league="NFL"]').click()
                page.locator(".pick").first.wait_for(timeout=15000)
                nfl_count=page.locator(".pick").count()
                assert nfl_count>0,"No NFL tracker cards from published standard lines"
                page.locator(".pick").first.click()
                page.locator("#detail:not(.hidden)").wait_for()
                assert page.locator("#detail-content .hero").count()==1,"NFL player detail did not render"
                # UI-only fixture: actual hosted outputs are verified separately.
                page.evaluate("""() => {state.picked={...state.picked,matchupPreview:{
                    rate:0.61,asOf:state.picked.captured,sport:'NFL',
                    method:'NFL_MATCHUP_RESIDUAL_V1',calibrated:false}};renderDetail();}""")
                assert '~61%' in page.locator('#detail-content .hero').inner_text()
                assert 'NFL ensemble estimate' in page.locator('#detail-content .hero').inner_text()
                assert 'Uncalibrated research probability' in page.locator('#detail-content .hero').inner_text()
                page.evaluate("() => {delete state.picked.matchupPreview;renderDetail();}")
                assert 'MATCHUP HIT ESTIMATE UNAVAILABLE' in page.locator('#detail-content .hero').inner_text()

                page.locator("#back").click()
                page.locator('[data-view="live"]').click()
                page.locator('[data-league="NBA"]').click()
                nba_live_games=page.locator("[data-game]").count()
                assert nba_live_games>0,"Published NBA scoreboard games are missing from Live"
                page.locator("[data-game]").first.click()
                assert page.locator("#detail-content").get_by_text("Full published player box score",exact=False).count()>0
                assert page.locator("#detail-content").get_by_text("Saved pregame standard lines",exact=False).count()>0
                page.locator("#back").click()
                page.locator('[data-league="NFL"]').click()
                nfl_live_games=page.locator("[data-game]").count()
                assert nfl_live_games>0,"Published NFL scoreboard games are missing from Live"
                page.locator("[data-game]").first.click()
                assert page.locator("#detail-content").get_by_text("Full published player box score",exact=False).count()>0
                assert page.locator("#detail-content").get_by_text("Scoreboard",exact=True).count()>0
                assert not errors, f"Client-side JavaScript exceptions: {errors[:5]}"
                print(f"Version E Chromium PASS: {nba_count} NBA / {nfl_count} NFL forecast cards, {nba_live_games} NBA / {nfl_live_games} NFL live-scoreboard game cards")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__=="__main__":
    check()

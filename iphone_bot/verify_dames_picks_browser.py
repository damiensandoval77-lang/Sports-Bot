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
                page.locator(".pick").first.wait_for(timeout=15000)
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
                assert not errors, f"Client-side JavaScript exceptions: {errors[:5]}"
                print(f"Version E Chromium PASS: {nba_count} NBA tracker cards, {nfl_count} NFL cards, both detail pages")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__=="__main__":
    check()

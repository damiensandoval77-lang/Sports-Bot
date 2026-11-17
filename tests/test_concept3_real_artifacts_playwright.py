#!/usr/bin/env python3
"""Runs Concept #3 against the actual repo data files, WITHOUT paid APIs or deployment.
Not a production/live-site verification; screenshot artifacts are for PR review.
"""
import json
import time
import threading
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]/"docs"
OUTPUT=Path(__file__).resolve().parents[1]/"test-artifacts"
OUTPUT.mkdir(exist_ok=True)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass

def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/dames-picks/concept-3-connected.html"
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for width in (393,1448):
            page=browser.new_page(viewport={"width":width,"height":950},device_scale_factor=1)
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            # Photo rights still pending. Do not fetch copyrighted CDN assets during CI.
            page.add_init_script("window.DAMES_DISABLE_EXTERNAL_PHOTOS=true")
            page.goto(base,wait_until="domcontentloaded")
            for _ in range(600):
                banner=page.locator(".connected-banner").inner_text()
                if banner.startswith("NBA connected"): break
                if banner.startswith("Connected view failed"): raise AssertionError(banner)
                time.sleep(0.1)
            else: raise AssertionError("Real artifact stage failed to load: "+banner)
            assert "LeBron James" in page.locator(".hero h1").inner_text()
            assert "PHI" in page.locator(".hero .player-name small").inner_text()
            assert page.locator(".bar").count()>0, "Actual current_form player logs were not rendered"
            assert page.locator(".player-stats b").first.inner_text() != "25.8", "Old hardcoded design number leaked"
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Horizontal overflow"
            assert not errors, errors
            page.screenshot(path=str(OUTPUT/f"concept3-connected-real-{width}.png"),full_page=True)
            print("PASS actual repo artifacts",width,"banner=",banner)
            page.close()
        browser.close()
    server.shutdown()

if __name__=="__main__": main()

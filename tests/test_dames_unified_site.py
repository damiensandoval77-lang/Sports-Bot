#!/usr/bin/env python3
"""Release gate: Concept #3 is the homepage; original operational tools survive.
Local-only server, local repository fixtures, NO paid API or external network.
"""
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

DOCS=Path(__file__).resolve().parents[1]/"docs"
OUT=Path(__file__).resolve().parents[1]/"test-artifacts"
OUT.mkdir(exist_ok=True)

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass

def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=str(DOCS)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    host=f"http://127.0.0.1:{server.server_port}"
    url=host+"/dames-picks/"
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for w in (393,768,1448):
            page=browser.new_page(viewport={"width":w,"height":950},device_scale_factor=1)
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.add_init_script("window.DAMES_DISABLE_EXTERNAL_PHOTOS=true;window.DAMES_DISABLE_DIRECT_SCORES=true")
            page.route("**/*",lambda route:route.continue_() if route.request.url.startswith(host) else route.abort())
            page.goto(url,wait_until="domcontentloaded")
            page.locator(".unified-navigation .unified-tab").first.wait_for(state="attached",timeout=30000)
            assert page.locator(".unified-tab").count()==5
            assert page.locator('[data-workspace="tennis"]').count()==0
            assert page.locator(".panel").count()==10, "Concept3 panel layout must remain unchanged"
            assert page.locator("#unified-workspace").is_hidden()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "Landing page overflow"
            page.screenshot(path=str(OUT/f"dames-unified-home-{w}.png"),full_page=True)
            page.locator(".ds5-side-nav button").filter(has_text="Dame\'s Picks").first.click()
            page.locator('[data-workspace="board"]').click()
            assert page.locator("#unified-workspace").is_visible()
            old=page.frame_locator("#unified-frame")
            old.locator('[data-view="board"]').wait_for(timeout=35000)
            expect(old.locator('[data-view="board"]')).to_have_class("active",timeout=10000)
            expect(old.locator('[data-league="NBA"]')).to_have_class("active",timeout=10000)
            page.locator('[data-workspace="saved"]').click()
            for i in range(70):
                if "active" in (old.locator('[data-view="saved"]').get_attribute("class") or ""):break
                time.sleep(.1)
            else:raise AssertionError("Saved not switched within same website")
            page.locator('[data-workspace="live"]').click()
            expect(old.locator('[data-view="live"]')).to_have_class("active",timeout=10000)
            page.locator('[data-workspace="tracker"]').click()
            expect(old.locator('[data-view="tracker"]')).to_have_class("active",timeout=10000)
            assert old.locator('[data-league="TENNIS"]').count()==0
            page.screenshot(path=str(OUT/f"dames-unified-tools-{w}.png"),full_page=True)
            page.locator('[data-workspace="player"]').click()
            assert page.locator(".wrap").is_visible()
            assert page.locator("#unified-workspace").is_hidden()
            assert not errors, errors
            print(f"PASS {w}px: Concept3 homepage; Board, Saved, Live, Tracker; no JS exceptions")
            page.close()
        browser.close()
    server.shutdown()
if __name__=="__main__":main()

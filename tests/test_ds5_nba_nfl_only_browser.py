"""Local-browser acceptance for the two-sport DS5 release. Never calls a paid provider."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

DOCS = Path(__file__).resolve().parents[1] / "docs"

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_):
        pass

def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=str(DOCS)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            for width in (393,768,1448):
                page=browser.new_page(viewport={"width":width,"height":900})
                requested=[]
                page.on("request",lambda r:requested.append(r.url))
                page.add_init_script("window.DAMES_DISABLE_EXTERNAL_PHOTOS=true;window.DAMES_DISABLE_DIRECT_SCORES=true")
                page.route("**/*",lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
                resp=page.goto(base+"/dames-picks/",wait_until="domcontentloaded",timeout=45000)
                assert resp is not None and resp.status==200
                page.locator(".unified-navigation button[data-workspace]").first.wait_for(state="attached",timeout=20000)
                workspaces=page.locator(".unified-navigation button[data-workspace]").evaluate_all(
                    "(nodes)=>nodes.map(el=>el.dataset.workspace)")
                assert workspaces==["player","board","live","tracker","saved"],workspaces
                page.locator(".sport-nav button").first.wait_for(state="attached",timeout=15000)
                sports=page.locator(".sport-nav button").all_text_contents()
                assert sports==["NBA","NFL"],sports
                page.evaluate("window.DamesUnifiedUI.open('board')")
                frame=page.frame_locator("#unified-frame")
                frame.locator('button[data-league="NBA"]').wait_for(state="attached",timeout=20000)
                legacy=frame.locator("button[data-league]").evaluate_all(
                    "(nodes)=>nodes.map(el=>el.dataset.league)")
                assert legacy==["NBA","NFL"],legacy
                frame.locator('button[data-league="NFL"]').click()
                assert frame.locator('button[data-league="NFL"]').get_attribute("class")=="active"
                frame.locator('button[data-league="NBA"]').click()
                assert frame.locator('button[data-league="NBA"]').get_attribute("class")=="active"
                assert not any("tennis" in u.lower() for u in requested),requested
                print(f"PASS {width}px: NBA/NFL-only UI, workspace and switcher; no removed provider requests",flush=True)
                page.close()
            browser.close()
    finally:
        server.shutdown()

if __name__=="__main__":
    main()

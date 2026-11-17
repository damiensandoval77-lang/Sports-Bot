#!/usr/bin/env python3
"""Local browser smoke for Cloudflare-only Market Explorer.
All REST responses mocked; NEVER contacts The Odds API or Cloudflare account.
"""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from playwright.sync_api import sync_playwright

DIST=Path(__file__).resolve().parents[1]/"cloudflare/dames-picks/dist"
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_): pass
CATALOG={"leagues":{
  "NBA":{"markets":[
    {"key":"player_points","stat":"PTS","label":"Points","tier":"core","bet_type":"over_under"},
    {"key":"player_threes","stat":"3PM","label":"Three-pointers made","tier":"expanded","bet_type":"over_under"},
    {"key":"player_double_double","stat":"DOUBLE_DOUBLE","label":"Double-double","tier":"milestone","bet_type":"yes_no"}
  ]},
  "NFL":{"markets":[{"key":"player_reception_yds","stat":"REC_YDS","label":"Receiving yards","tier":"core","bet_type":"over_under"}]}
}}
ROWS=[{"league":"NBA","event_id":"example_1234567890","event_start":"2026-11-19T00:00:00Z",
 "matchup":"New York Knicks @ Boston Celtics","bookmaker":"prizepicks","market_key":"player_points",
 "player":"Player Example","line":24.5,"line_change":None,"over_price":None,"under_price":None,
 "bookmaker_price_type":"indicative_dfs","sportsbook_no_vig_over":None,"observed_at":"2026-11-18T23:45:00Z"}]
def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=str(DIST)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        for width in (393,1448):
            page=browser.new_page(viewport={"width":width,"height":900},device_scale_factor=1)
            errors=[]
            external=[]
            page.on("pageerror",lambda e: errors.append(str(e)))
            def routes(route):
                u=urlsplit(route.request.url)
                if not route.request.url.startswith(base):
                    external.append(route.request.url)
                    route.abort();return
                if u.path=="/api/v1/odds/catalog":
                    body=CATALOG;code=200
                elif u.path=="/api/v1/odds/budget":
                    body={"status":"ok","config":{"collection_enabled":False,"monthly_cap":None,"daily_cap":None},
                          "usage":{"used_credits":0}};code=200
                elif u.path=="/api/v1/odds/board":
                    league=parse_qs(u.query).get("league",["NBA"])[0]
                    body={"status":"available" if league=="NBA" else "no_recent_standard_lines",
                          "quotes":ROWS if league=="NBA" else []};code=200
                else:
                    route.continue_();return
                route.fulfill(status=code,content_type="application/json",body=json.dumps(body))
            page.route("**/*",routes)
            page.goto(base+"/dames-picks/market-explorer.html",wait_until="domcontentloaded")
            page.locator(".market").first.wait_for(timeout=10000)
            assert page.locator(".market").count()==3
            assert page.locator("#collection").inner_text()=="Off"
            assert page.locator("#credits").inner_text()=="0"
            page.locator("#board tbody tr").first.wait_for(timeout=10000)
            assert page.locator("#board tbody tr").count()==1
            assert "DFS: indicative" in page.locator("#board").inner_text()
            assert "—" in page.locator("#board").inner_text()
            page.locator("#search").fill("Three")
            assert page.locator(".market").count()==1
            assert "Three-pointers" in page.locator(".market").inner_text()
            page.locator('[data-league="NFL"]').click()
            assert page.locator(".market").count()==1
            assert page.locator("#board-empty").is_visible()
            assert not page.locator("#board").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"),"Horizontal overflow"
            assert not external,external
            assert not errors,errors
            print(f"PASS {width}px: market catalog, cached rows, no fake DFS probabilities, no paid browser requests")
            page.close()
        browser.close()
    finally:
      server.shutdown()
if __name__=="__main__":main()

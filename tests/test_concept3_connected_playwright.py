#!/usr/bin/env python3
"""Local isolated browser QA for connected Concept #3. No external network or paid API calls."""
import base64
import json
import time
import threading
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]/"docs"
PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6d7uoAAAAASUVORK5CYII=")
start=(datetime.now(timezone.utc)+timedelta(hours=15)).isoformat()
form={"updated_at":datetime.now(timezone.utc).isoformat(),"source":"Test fixture, independent game logs",
      "players":[{"player":"LeBron James","player_id":"2544","team":"PHI","games":2,
                  "metrics":{"PTS":{"season":20,"l5":20,"l10":None},"REB":{"season":6.5,"l5":6.5},
                             "AST":{"season":4,"l5":4},"PRA":{"season":30.5,"l5":30.5}},
                  "log":[["2026-11-15","BOS",18,6,5,29,34],["2026-11-16","NYK",22,7,3,32,35]]}]}
schedule={"games":[{"id":"4019example","game":"Philadelphia 76ers @ Boston Celtics",
                    "home":"Boston Celtics","away":"Philadelphia 76ers",
                    "home_abbreviation":"BOS","away_abbreviation":"PHI","start":start,
                    "game_state":"pre","away_score":None,"home_score":None}]}
fixtures={
"/current_form.json":form,
"/nba_schedule.json":schedule,
"/nba_scoreboard_independent.json":{"is_live_score_source":False,"games":[]},
"/lagged_matchup_all_market_ledger.json":{"status":"FROZEN_NEW_AI_ALL_MARKET","records":[]},
"/prizepicks_pregame_line_archive.json":{"quotes":[]},
"/nba_confidence_calibration.json":{"status":"UNAVAILABLE","records":[]},
"/nfl/data/schedule_2026.json":{"games":[]},
"/nfl/data/latest_2026.json":{"files":[]},
"/nfl/data/active_frozen_2026.json":{"scope":"EXACT_ARCHIVED_PREGAME_ROWS","records":[],"season":2026},
}
teams={"sports":[{"leagues":[{"teams":[{"team":{"id":"20","abbreviation":"PHI"}}]}]}]}
roster={"athletes":[{"id":"1966","displayName":"LeBron James",
                     "headshot":{"href":"https://a.espncdn.com/i/headshots/nba/players/full/1966.png"}}]}

def main():
    Handler=partial(SimpleHTTPRequestHandler,directory=str(ROOT))
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    task=threading.Thread(target=server.serve_forever,daemon=True)
    task.start()
    base=f"http://127.0.0.1:{server.server_port}/dames-picks/concept-3-connected.html"
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for width in (393,768,1448):
            page=browser.new_page(viewport={"width":width,"height":900},device_scale_factor=1)
            errors=[]
            page.on("pageerror",lambda err:errors.append(str(err)))
            def fixture_route(route):
                path=route.request.url.split("?")[0]
                if path.startswith("https://site.api.espn.com/"):
                    body=roster if path.endswith("/roster") else teams
                    route.fulfill(status=200,body=json.dumps(body),content_type="application/json",
                                  headers={"Access-Control-Allow-Origin":"*"})
                elif path.startswith("https://a.espncdn.com/"):
                    route.fulfill(status=200,body=PNG,content_type="image/png")
                else:
                    key=__import__("urllib.parse",fromlist=["urlsplit"]).urlsplit(path).path
                    if key.startswith("/nfl/"): key=key
                    if key in fixtures:
                        route.fulfill(status=200,body=json.dumps(fixtures[key]),content_type="application/json")
                    else:
                        route.continue_()
            page.route("**/*",fixture_route)
            page.goto(base,wait_until="domcontentloaded")
            for _ in range(300):
                if "NBA connected" in page.locator(".connected-banner").inner_text(): break
                time.sleep(.1)
            else:
                raise AssertionError("Connected NBA view did not finish: "+page.locator(".connected-banner").inner_text())
            assert page.locator(".hero h1").inner_text().startswith("LeBron James")
            assert "PHI" in page.locator(".hero .player-name small").inner_text()
            assert "BOS" in page.locator(".next-match").inner_text()
            assert page.locator(".bar").count()==2
            photo=page.locator(".portrait img")
            photo.wait_for(state="visible",timeout=10000)
            assert "/1966.png" in photo.get_attribute("src"), "Must use ESPN roster's verified ID, not a non-ESPN player ID"
            assert page.locator("#model-proj").inner_text()=="—"
            assert page.locator("#games-avg").inner_text()=="20.0"
            assert "Unavail" in page.locator("#teammates").inner_text() or "Not available" in page.locator("#teammates").inner_text()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),"Horizontal overflow"
            if width==393:
                assert page.locator("#mobile-player-search").is_visible()
                page.locator(".sport-nav button",has_text="NFL").click()
                for _ in range(150):
                    if "NFL linked" in page.locator(".connected-banner").inner_text(): break
                    time.sleep(.1)
                else:
                    raise AssertionError("NFL view did not link: "+page.locator(".connected-banner").inner_text())
                page.locator(".sport-nav button",has_text="NBA").click()
                assert 'NBA' in page.locator('.connected-banner').inner_text() or page.locator('.sport-nav button.selected').inner_text() == 'NBA'
            assert not errors, errors
            print(f"PASS {width}px connected fixture: current team, real logs, no made-up prop, layout, filters")
            page.close()
        browser.close()
    server.shutdown()

if __name__=="__main__":main()

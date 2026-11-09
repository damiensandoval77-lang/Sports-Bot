"""Independent real Chromium check of the deployed Sports-Bot AI cards.

Unlike source-file or HTTP checks, this executes the public site's JavaScript
and verifies genuine provider line + AI projection elements in rendered DOM.
No account secrets, wagers, paid provider calls, or stored browser sessions.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"docs/browser_card_probe.json"
URL=os.environ.get("SPORTS_BOT_PUBLIC_SITE_URL","https://damiensandoval77-lang.github.io/Sports-Bot/")
EXPECTED={"Cleveland Cavaliers @ Charlotte Hornets",
          "Los Angeles Lakers @ Atlanta Hawks",
          "Washington Wizards @ Detroit Pistons",
          "Memphis Grizzlies @ Toronto Raptors",
          "Indiana Pacers @ Dallas Mavericks",
          "Denver Nuggets @ Houston Rockets",
          "San Antonio Spurs @ Phoenix Suns",
          "New Orleans Pelicans @ Golden State Warriors"}

def assess(board_count,labels,tiles,errors,now,per_game=None):
    reasons=[]
    if board_count==0:
        reasons.append("NO_RENDERED_PRIZEPICKS_AI_CARDS")
    if not labels:
        reasons.append("NO_RENDERED_LINE_AND_PROJECTION_VALUES")
    missing=sorted(EXPECTED-set(tiles))
    if missing:
        reasons.append("OFFICIAL_NBA_GAMES_MISSING_NAVIGATION")
    unmatched=sorted(game for game in EXPECTED if per_game is not None and per_game.get(game,0)<1)
    if unmatched:
        reasons.append("SCHEDULED_GAME_WITHOUT_RENDERED_PP_AI_CARDS")
    return {
        "checked_at":now.isoformat(),
        "status":"READY" if not reasons else "DEGRADED",
        "browser_render_verified":not reasons,
        "rendered_ai_cards":board_count,
        "line_and_projection_cards":len(labels),
        "game_tiles_seen":sorted(set(tiles)),
        "missing_official_games":missing,
        "games_without_rendered_matches":unmatched,
        "rendered_matches_by_game":per_game or {},
        "reasons":reasons,
        "browser_errors":errors[:8],
        "public_site":URL,
        "note":"Executed public browser DOM; research matches, not verified wagering picks or complete vendor coverage."
    }

def probe():
    from playwright.sync_api import sync_playwright
    now=dt.datetime.now(dt.timezone.utc)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":390,"height":844},
                                  device_scale_factor=2,
                                  locale="en-US",timezone_id="America/New_York")
            page.on("pageerror",lambda e:errors.append(str(e)[:240]))
            response=page.goto(URL,wait_until="domcontentloaded",timeout=45000)
            if response is None or response.status!=200:
                raise RuntimeError("Public dashboard HTTP status not 200")
            try:
                page.wait_for_function(
                    "() => document.querySelector('#ai-total')?.textContent?.includes('authentic PrizePicks line matches')",
                    timeout=30000)
            except Exception:
                errors.append("DID_NOT_RENDER_AUTHENTIC_PRIZEPICKS_AI_SUMMARY")
            cards=page.locator("#ai-board article.compact-prop")
            count=cards.count()
            present=[]
            # Verify actual rendered line and projection values rather than
            # confusing no-line cards with provider-backed cards.
            for item in cards.all()[:300]:
                labels=item.locator(".ai-metric-label").all_inner_texts()
                values=item.locator(".ai-metric-value").all_inner_texts()
                text=item.inner_text()
                if "PRIZEPICKS LINE" in labels and "AI PROJECTION" in labels and (
                    "PRIZEPICKS + INDEPENDENT AI" in text
                ) and len(values)>=2 and all(v.strip() not in ("","—","Unavailable") for v in values[:2]):
                    present.append(text.splitlines()[0][:75])
            game_tiles=page.locator("#game-strip button.score-tile").all()
            tiles=[t.get_attribute("aria-label") or "" for t in game_tiles]
            recognized=[game for game in EXPECTED if any(game in label for label in tiles)]
            # Crucial end-to-end check: a game tab existing does not prove it
            # actually filters to PrizePicks/AI cards. Click every official
            # game and confirm at least one identity-matched research card.
            per_game={}
            for game in sorted(EXPECTED):
                tile=next((t for t in game_tiles if game in (t.get_attribute("aria-label") or "")),None)
                if tile is None:
                    per_game[game]=0
                    continue
                try:
                    tile.click(timeout=6000)
                    names=page.locator("#ai-board article.compact-prop .compact-identity .match").all_inner_texts()
                    per_game[game]=sum(game in name for name in names)
                except Exception as exc:
                    errors.append("GAME_FILTER_FAILED:"+game+":"+type(exc).__name__)
                    per_game[game]=0
            page.locator("#game-strip button.all-games").click(timeout=6000)
            result=assess(count,present,recognized,errors,now,per_game)
            result["ai_summary"]=page.locator("#ai-total").inner_text()[:240]
            result["public_status"]=page.locator("#status").inner_text()[:120]
            return result
        finally:
            browser.close()

def main():
    now=dt.datetime.now(dt.timezone.utc)
    try:
        output=probe()
    except Exception as e:
        output={"checked_at":now.isoformat(),"status":"DEGRADED",
                "browser_render_verified":False,"rendered_ai_cards":0,
                "line_and_projection_cards":0,"missing_official_games":sorted(EXPECTED),
                "reasons":["PUBLIC_BROWSER_PROBE_FAILED"],
                "browser_errors":[type(e).__name__+":"+str(e)[:280]],
                "public_site":URL}
    REPORT.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print("PUBLIC BROWSER RENDER:",json.dumps(output,sort_keys=True))
    if output["status"]!="READY":
        sys.exit(1)

if __name__=="__main__":
    main()

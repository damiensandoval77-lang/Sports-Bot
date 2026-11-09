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

def assess(board_count, standard_lines, tiles, errors, now, per_game=None,
           modeled_count=0, line_only_count=0, expected_games=None):
    """Separate actual rendered standard quote coverage from modeled AI coverage.

    A line without a projection is visible and truthful, but NOT an AI pick.
    Old 20K SIM estimates were intentionally phased out; requiring them would
    permanently false-alarm on the new PTS/REB/AST/PRA architecture.
    """
    expected=set(EXPECTED if expected_games is None else expected_games)
    reasons=[]
    if expected and board_count==0:
        reasons.append("NO_RENDERED_NBA_MARKET_CARDS")
    if expected and not standard_lines:
        reasons.append("NO_RENDERED_STANDARD_PRIZEPICKS_LINES")
    missing=sorted(expected-set(tiles))
    if missing:reasons.append("SCHEDULED_GAMES_MISSING_NAVIGATION")
    unmatched=sorted(g for g in expected if per_game is not None and per_game.get(g,0)<1)
    if unmatched:reasons.append("UPCOMING_GAME_WITHOUT_STANDARD_LINE_CARD")
    if expected and modeled_count==0:
        reasons.append("NEW_AI_MODEL_CARDS_NOT_RENDERED")
    state="NO_UPCOMING_GAMES" if not expected else "READY" if not reasons else "DEGRADED"
    return {
        "checked_at":now.isoformat(),
        "status":state,"browser_render_verified":not reasons,
        "rendered_ai_cards":board_count,
        "verified_standard_line_cards":len(standard_lines),
        "rendered_new_ai_probability_cards":modeled_count,
        "verified_line_only_cards":line_only_count,
        "new_ai_model_coverage_partial":modeled_count<board_count,
        "game_tiles_seen":sorted(set(tiles)),
        "expected_upcoming_games":sorted(expected),
        "missing_official_games":missing,
        "games_without_rendered_matches":unmatched,
        "rendered_matches_by_game":per_game or {},
        "reasons":reasons,"browser_errors":errors[:8],
        "public_site":URL,
        "note":"Independent public Chromium DOM proof of real standard PrizePicks lines. Missing new AI projections are explicitly —, not simulated."
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
                    "() => [...document.querySelectorAll('#ai-board article.compact-prop .ai-metric-label')].some(e => e.textContent.includes('PRIZEPICKS STD'))",
                    timeout=23000)
            except Exception:
                errors.append("STANDARD_PRIZEPICKS_AI_BOARD_NOT_RENDERED")
            # Only upcoming fixtures should have live pretip projection cards.
            # A started game must have its frozen picks in matchup/tracker,
            # not be misclassified as an absent new pregame market.
            expected=page.evaluate("""() => {
              const now=Date.now();
              if(typeof nbaSchedule==='undefined'||!nbaSchedule?.games)return [];
              return nbaSchedule.games.filter(g =>
                 g.game_state==='pre' && Date.parse(g.start)>now &&
                 new Date(g.start).toLocaleDateString('en-CA',{timeZone:'America/New_York'})===
                 new Date().toLocaleDateString('en-CA',{timeZone:'America/New_York'})
              ).map(g=>g.game);
            }""")
            expected=set(expected)&EXPECTED
            cards=page.locator("#ai-board article.compact-prop")
            count=cards.count()
            labels_found=[]
            modeled=0
            quotes_only=0
            for item in cards.all()[:400]:
                labels=item.locator(".ai-metric-label").all_inner_texts()
                values=item.locator(".ai-metric-value").all_inner_texts()
                if "PRIZEPICKS STD" not in labels:continue
                pos=labels.index("PRIZEPICKS STD")
                if pos>=len(values) or values[pos].strip() in ("","—","Unavailable"):
                    continue
                labels_found.append(item.inner_text().splitlines()[0][:75])
                pi=labels.index("NEW AI PROJECTION") if "NEW AI PROJECTION" in labels else -1
                ci=labels.index("NEW AI CHANCE") if "NEW AI CHANCE" in labels else -1
                valid_model=(pi>=0 and ci>=0 and len(values)>max(pi,ci) and
                    values[pi].strip() not in ("","—","Unavailable") and
                    values[ci].strip().endswith("%"))
                if valid_model:modeled+=1
                else:quotes_only+=1
            tiles=page.locator("#game-strip button.score-tile").all()
            tile_names=[t.get_attribute("aria-label") or "" for t in tiles]
            recognized=[g for g in EXPECTED if any(g in label for label in tile_names)]
            per_game={}
            for game in sorted(expected):
                tile=next((t for t in tiles if game in (t.get_attribute("aria-label") or "")),None)
                if tile is None:
                    per_game[game]=0
                    continue
                try:
                    tile.click(timeout=6000)
                    match=page.locator("#ai-board article.compact-prop .compact-identity .match").all_inner_texts()
                    per_game[game]=sum(game in label for label in match)
                except Exception as exc:
                    errors.append("GAME_FILTER_FAILED:"+game+":"+type(exc).__name__)
                    per_game[game]=0
            result=assess(count,labels_found,recognized,errors,now,per_game,
                          modeled_count=modeled,line_only_count=quotes_only,
                          expected_games=expected)
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

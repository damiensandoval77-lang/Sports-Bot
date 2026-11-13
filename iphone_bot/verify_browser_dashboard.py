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
URL=os.environ.get("SPORTS_BOT_PUBLIC_SITE_URL","https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/")
EXPECTED={"Cleveland Cavaliers @ Charlotte Hornets",
          "Los Angeles Lakers @ Atlanta Hawks",
          "Washington Wizards @ Detroit Pistons",
          "Memphis Grizzlies @ Toronto Raptors",
          "Indiana Pacers @ Dallas Mavericks",
          "Denver Nuggets @ Houston Rockets",
          "San Antonio Spurs @ Phoenix Suns",
          "New Orleans Pelicans @ Golden State Warriors"}

def assess(board_count,labels,tiles,errors,now,per_game=None,simulation_count=None,standard_lines=0,model_chances=0,diagnostics=None,expected_games=None,required_upcoming=None):
    reasons=[]
    if errors:reasons.append("UNHANDLED_JS_ERRORS")
    expected=set(EXPECTED if expected_games is None else expected_games)
    upcoming=set(expected if required_upcoming is None else required_upcoming)
    if not upcoming.issubset(expected):
        reasons.append("UPCOMING_GAME_NOT_IN_OFFICIAL_SCHEDULE")
    if upcoming and board_count==0:
        reasons.append("NO_RENDERED_PRIZEPICKS_AI_CARDS")
    if upcoming and standard_lines==0:
        reasons.append("NO_RENDERED_VERIFIED_STANDARD_LINES")
    if upcoming and model_chances==0:
        reasons.append("NO_RENDERED_NEW_AI_CHANCES")
    missing=sorted(expected-set(tiles))
    if missing:
        reasons.append("OFFICIAL_NBA_GAMES_MISSING_NAVIGATION")
    unmatched=sorted(game for game in upcoming if per_game is not None and per_game.get(game,0)<1)
    if unmatched:
        reasons.append("SCHEDULED_GAME_WITHOUT_RENDERED_PP_AI_CARDS")
    return {
        "checked_at":now.isoformat(),
        "status":"READY" if not reasons else "DEGRADED",
        "browser_render_verified":not reasons,
        "rendered_ai_cards":board_count,
        "rendered_verified_standard_lines":standard_lines,
        "rendered_new_ai_chances":model_chances,
        "diagnostics":diagnostics or {},
        "line_and_projection_cards":len(labels),
        "rendered_20k_simulation_cards":simulation_count,
        "game_tiles_seen":sorted(set(tiles)),
        "scheduled_game_count":len(expected),
        "upcoming_game_count":len(upcoming),
        "upcoming_games_checked":sorted(upcoming),
        "missing_official_games":missing,
        "games_without_rendered_matches":unmatched,
        "rendered_matches_by_game":per_game or {},
        "reasons":reasons,
        "browser_errors":errors[:8],
        "public_site":URL,
        "note":"Executed public browser DOM; research matches, not verified wagering picks or complete vendor coverage."
    }

def probe():
    """Check the current unified DOM and current official slate at phone width."""
    from playwright.sync_api import sync_playwright
    now=dt.datetime.now(dt.timezone.utc)
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":390,"height":844},
                                  locale="en-US",timezone_id="America/New_York")
            page.on("pageerror",lambda e:errors.append(str(e)[:240]))
            response=page.goto(URL,wait_until="domcontentloaded",timeout=45000)
            if response is None or response.status!=200:raise RuntimeError("Public dashboard HTTP status not 200")
            page.wait_for_function("() => typeof state!=='undefined' && !!state.updated && !state.loading",timeout=60000)
            page.locator('button[data-league="NBA"]').click()
            page.locator('button[data-view="board"]').click()
            obs=page.evaluate("""() => {
              const sch=state.raw?.nbaSchedule;
              const day=new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York'}).format(new Date());
              const games=(sch?.games||[]).filter(g=>g.date_eastern===day);
              const cards=[...document.querySelectorAll('#cards button.pick[data-id]')];
              const models=new Map(state.nba.map(p=>[m.key(p),p]));
              const perGame={}, names=[];let standard=0,chances=0;
              for(const card of cards){
                const p=models.get(card.dataset.id),values=[...card.querySelectorAll('.stat-grid strong')].map(x=>x.textContent.trim());
                if(!p||p.quoteOnly||p.source!=='PrizePicks'||values.length<3||!Number.isFinite(Number(values[0]))||!Number.isFinite(Number(values[1])))continue;
                standard++;names.push(p.player);perGame[p.game]=(perGame[p.game]||0)+1;
                if(/[0-9]/.test(values[2]))chances++;
              }
              return {cards:cards.length,names,standard,chances,perGame,
                expected:games.map(g=>g.game),upcoming:games.filter(g=>Date.parse(g.start)>Date.now()).map(g=>g.game),
                scheduleUsable:sch?.coverage_complete===true&&sch?.dates_eastern?.includes(day)===true};
            }""")
            page.locator('button[data-view="live"]').click()
            tiles=page.evaluate("""() => [...document.querySelectorAll('#cards button[data-game]')].map(b=>
              state.liveGames.find(g=>g.sport+'|'+g.gameId===b.dataset.game)?.game).filter(Boolean)""")
            result=assess(obs['cards'],obs['names'],tiles,errors,now,obs['perGame'],
                          standard_lines=obs['standard'],model_chances=obs['chances'],
                          expected_games=obs['expected'],required_upcoming=obs['upcoming'],
                          diagnostics={"scheduleUsable":obs['scheduleUsable'],"viewport":{"width":390,"height":844}})
            if not obs['scheduleUsable']:
                result['reasons'].append('OFFICIAL_SLATE_DIAGNOSTICS_MISSING')
                result['status']='DEGRADED';result['browser_render_verified']=False
            return result
        finally:browser.close()

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

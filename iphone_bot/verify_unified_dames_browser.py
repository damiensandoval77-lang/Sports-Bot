"""Independent Chromium test of the ONLY public Dame's Picks NBA+NFL app.

This does not touch provider APIs, wager, fabricate records or read secrets.
Checks real GitHub Pages JavaScript, both league tabs and rendered saved cards.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/dames-picks/browser_readiness.json"
URL=os.environ.get("DAMES_PICKS_UNIFIED_URL","https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/")

def assess(nba,nfl,errors, *, app_title, url=URL, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    reasons=[]
    if "NBA + NFL" not in app_title:reasons.append("NOT_UNIFIED_APP")
    for sport,obs in (("NBA",nba),("NFL",nfl)):
        if obs.get("selected") != sport:reasons.append(sport+"_TAB_NOT_SELECTED")
        if not obs.get("loaded"):reasons.append(sport+"_DATA_NOT_LOADED")
        if obs.get("rows",0)<1:reasons.append(sport+"_NO_SAVED_RECORDS")
        if obs.get("rows",0)>0 and obs.get("rendered",0)<1:reasons.append(sport+"_NO_RENDERED_PICK_CARDS")
        # A historical-card-only browser success is not a working LIVE app.
        # The current schedule determines whether a game should have scores
        # and players. A 15-minute tipoff grace permits provider delay.
        expected=obs.get("live_expected")
        if not isinstance(expected,int) or expected<0:
            reasons.append(sport+"_LIVE_COVERAGE_NOT_TESTED")
        elif expected>0:
            if obs.get("live_missing",0)>0:
                reasons.append(sport+"_STARTED_GAMES_MISSING_LIVE_DATA")
            if obs.get("score_missing",0)>0:
                reasons.append(sport+"_STARTED_GAMES_MISSING_SCORES")
            if obs.get("player_missing",0)>0:
                reasons.append(sport+"_STARTED_GAMES_MISSING_PLAYERS")
        # A partially loaded NFL export can still leave many visible cards.
        # The site's own warning must not be masked by a nonzero card count.
        observed_errors=obs.get("errors") or []
        markers=("NFL feed partially loaded","NFL export unavailable",
                 "NFL permanent grading ledgers unavailable") if sport=="NFL" else (
                 "NBA frozen ledger unavailable","NBA standard quote archive unavailable")
        if any(any(marker in str(err) for marker in markers) for err in observed_errors):
            reasons.append(sport+"_REQUIRED_FEED_ERRORS")
    if errors:reasons.append("UNHANDLED_JS_ERRORS")
    return {"checked_at":now.isoformat(),"status":"READY" if not reasons else "DEGRADED",
            "browser_render_verified":not reasons,"site_url":url,
            "app_title":app_title,"NBA":nba,"NFL":nfl,
            "reasons":reasons,"browser_errors":errors[:10],
            "note":"Real merged-app DOM check. Not proof every live prop has a line, that feeds are fresh, or that grades are complete."}

def probe():
    from playwright.sync_api import sync_playwright
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":390,"height":844},
                                  device_scale_factor=2,
                                  locale="en-US",timezone_id="America/New_York")
            page.on("pageerror",lambda e: errors.append(str(e)[:240]))
            response=page.goto(URL,wait_until="domcontentloaded",timeout=45000)
            if response is None or response.status != 200:
                raise RuntimeError("Unified app HTTP status not 200")
            page.wait_for_function("() => typeof state !== 'undefined' && !!state.updated && !state.loading",timeout=60000)
            # Initial page load may complete before the app's asynchronous
            # browser-direct scoreboard/boxscore refresh. Test live state
            # AFTER one completed forced refresh, not a transient race.
            page.wait_for_function("() => !state.liveBusy",timeout=45000)
            direct=page.evaluate("""async () => {
              if(typeof liveTick!=="function")return {attempted:false,reason:"NO_LIVE_REFRESH_FUNCTION"};
              await liveTick(true);
              return {attempted:true,received:!!state.direct,
                directGames:state.direct?.feed?.games?.length||0,
                directScores:state.direct?.board?.games?.length||0,
                directErrors:state.direct?.feed?.errors?.slice?.(0,8)||[],
                at:state.directAt||null};
            }""")
            page.wait_for_function("() => !state.liveBusy",timeout=45000)
            title=page.title()
            result={}
            for sport in ("NBA","NFL"):
                page.locator('button[data-league="'+sport+'"]').click(timeout=10000)
                # Tracker shows original saved records even when today's
                # pregame board is intentionally empty after tipoff.
                page.locator('button[data-view="tracker"]').click(timeout=10000)
                page.wait_for_timeout(400)
                observation=page.evaluate("""sport => ({
                  selected:state.league,
                  loaded:!!state.updated && !state.loading,
                  rows:sport==="NBA"?state.nba.length:state.nfl.length,
                  rendered:document.querySelectorAll('#cards .pick').length,
                  ...(() => {
                    // Catch live feed failures the archived tracker used to
                    // hide. Only require data for this league's matchups
                    // 15 minutes–4 hours after scheduled tipoff; no guesses.
                    const now=Date.now(), active=(sport==="NBA"?state.liveGames:state.liveGames)
                      .filter(g=>g.sport===sport && (
                        g.state==="in" || (
                          Number.isFinite(Date.parse(g.start)) &&
                          now-Date.parse(g.start)>=15*60000 &&
                          now-Date.parse(g.start)<=4*3600000 &&
                          g.state!=="final"
                        )
                      ));
                    return {
                      live_expected:active.length,
                      live_missing:active.filter(g=>!g.fresh ||
                        !g.observedAt || g.state==="unknown" || g.state==="stale").length,
                      score_missing:active.filter(g=>g.awayScore==null || g.homeScore==null).length,
                      player_missing:active.filter(g=>!Array.isArray(g.players)||g.players.length===0).length
                    };
                  })(),
                  errors:state.errors.slice(0,12),
                  status:document.querySelector('#status')?.textContent?.slice(0,250)
                })""",sport)
                result[sport]=observation
            report=assess(result["NBA"],result["NFL"],errors,app_title=title)
            report["browser_direct_probe"]=direct
            if not direct.get("attempted"):
                report["reasons"].append("BROWSER_DIRECT_REFRESH_NOT_TESTED")
                report["status"]="DEGRADED"
                report["browser_render_verified"]=False
            return report
        finally:
            browser.close()

def main():
    try:report=probe()
    except Exception as exc:
        report={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                "status":"DEGRADED","browser_render_verified":False,
                "site_url":URL,"reasons":["UNIFIED_BROWSER_PROBE_FAILED"],
                "browser_errors":[type(exc).__name__+":"+str(exc)[:250]]}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("UNIFIED_BROWSER",json.dumps(report))
    if report["status"]!="READY":sys.exit(1)

if __name__=="__main__":main()

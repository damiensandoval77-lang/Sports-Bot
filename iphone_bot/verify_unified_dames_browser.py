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

def assess_live_order(observation):
    """Check rendered fixture identities/order independently of the UI sorter."""
    reasons=[]
    if observation.get("selected") != observation.get("sport") or observation.get("mode") != "live":
        reasons.append("LIVE_VIEW_NOT_SELECTED")
    expected=observation.get("expected_ids",[])
    cards=observation.get("cards",[])
    ids=[card.get("id") for card in cards]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):
        reasons.append("LIVE_FIXTURE_RENDER_MISMATCH")
    priorities={"in":0,"stale":1,"final":2,"scheduled":3,"unknown":4}
    previous=None
    for card in cards:
        rank=priorities.get(card.get("state"),4)
        try:
            start=dt.datetime.fromisoformat(card.get("start", "").replace("Z","+00:00")).timestamp()
        except (ValueError,TypeError,AttributeError):
            start=float("inf")
        key=(rank,start)
        if previous is not None and key<previous:
            reasons.append("LIVE_FIXTURES_OUT_OF_ORDER")
            break
        previous=key
    return list(dict.fromkeys(reasons))

def observe_live_order(page, sport):
    page.locator('button[data-league="'+sport+'"]').click(timeout=10000)
    page.locator('button[data-view="live"]').click(timeout=10000)
    # Rendering is synchronous. A click throwing inside the application must
    # not pass merely because Tracker's archived cards still remain visible.
    observed=page.evaluate("""sport => {
      const expected=m.currentSlateGames(state.liveGames,sport);
      const byId=new Map(expected.map(g=>[g.sport+"|"+g.gameId,g]));
      return {sport,selected:state.league,mode:state.mode,expected_ids:[...byId.keys()],
        cards:[...document.querySelectorAll('#cards [data-game]')].map(el=>{
          const id=el.dataset.game,g=byId.get(id);
          return {id,state:g?.state,start:g?.start||null,
                  text:el.textContent.slice(0,240)};
        })};
    }""",sport)
    observed["reasons"]=assess_live_order(observed)
    return observed

def assess_tennis(observation):
    """Validate distinct fixture-list and quote-only contracts, never forecasts."""
    reasons=[]
    mode=observation.get("mode")
    if observation.get("selected")!="TENNIS" or mode!=observation.get("requested_mode"):
        reasons.append("TENNIS_VIEW_NOT_SELECTED")
    if observation.get("metrics") != ["—","—","—"]:
        reasons.append("TENNIS_UNSUPPORTED_METRICS")
    fixtures=observation.get("fixtures",[])
    fixture_cards=observation.get("fixture_cards",[])
    notice=observation.get("notice", "")
    notice_ok=(all(x in notice for x in ("Partial list, not a live schedule", "Lines and estimates are unavailable"))
               if fixtures else "Projections, hit estimates and grading are unavailable" in notice)
    if not notice_ok:
        reasons.append("TENNIS_LIMITATION_NOTICE_MISSING")
    cards=observation.get("cards",[])
    ids=[c.get("id") for c in cards]
    expected=observation.get("expected_ids",[])
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected) or observation.get("game_cards",0):
        reasons.append("TENNIS_CROSS_LEAGUE_OR_MISSING_CARDS")
    if any(c.get("projection")!="—" or c.get("estimate")!="—" or c.get("grade")!="LINE ONLY" for c in cards):
        reasons.append("TENNIS_UNSUPPORTED_ESTIMATE_OR_GRADE")
    expected_fixtures=[(f.get("name"),f.get("date")) for f in fixtures]
    actual_fixtures=[(f.get("name"),f.get("date")) for f in fixture_cards]
    if (mode!="board" and (fixtures or fixture_cards)) or len(set(expected_fixtures))!=len(expected_fixtures) or actual_fixtures!=expected_fixtures:
        reasons.append("TENNIS_FIXTURE_IDENTITY_MISMATCH")
    if any(f.get("grade")!="MATCH LIST" or f.get("projection") is not None or f.get("estimate") is not None
           or f.get("has_quote_id") or f.get("has_stats") or "start time unconfirmed" not in f.get("context", "")
           or "no pick or hit estimate" not in f.get("note", "") for f in fixture_cards):
        reasons.append("TENNIS_UNSUPPORTED_FIXTURE_ESTIMATE_OR_GRADE")
    empty=observation.get("empty","")
    if mode in ("live","tracker"):
        if cards or "not connected" not in empty or "does not mean no matches" not in empty:
            reasons.append("TENNIS_UNSUPPORTED_LIVE_OR_GRADING")
    elif not cards and not fixture_cards and "not evidence that no tennis matches exist" not in empty:
        reasons.append("TENNIS_EMPTY_STATE_NOT_HONEST")
    if observation.get("research_visible"):
        reasons.append("TENNIS_CROSS_LEAGUE_RESEARCH_VISIBLE")
    if observation.get("viewport_width")!=390 or observation.get("overflow",0)>1:
        reasons.append("TENNIS_PHONE_LAYOUT_FAILED")
    return list(dict.fromkeys(reasons))

def observe_tennis(page):
    observations=[]
    # Enter from each populated league to detect retained cards and metrics.
    for previous in ("NBA","NFL"):
        page.locator('button[data-league="'+previous+'"]').click(timeout=10000)
        page.locator('button[data-view="board"]').click(timeout=10000)
        page.locator('button[data-league="TENNIS"]').click(timeout=10000)
        for mode in ("board","live","tracker","saved"):
            page.locator('button[data-view="'+mode+'"]').click(timeout=10000)
            obs=page.evaluate(r"""mode => ({
              selected:state.league, mode:state.mode, requested_mode:mode,
              metrics:['wl','rate','games'].map(id=>document.getElementById(id).textContent.trim()),
              notice:document.querySelector('#coverage')?.textContent||'',
              expected_ids:['live','tracker'].includes(mode)?[]:shown().map(p=>m.key(p)),
              fixtures:mode==='board'?(window.DamesPicksTennis?.fixtures?.(state.tennisFixtures,Date.now())||[])
                .filter(q=>q.players.join(' ').toLowerCase().includes(document.getElementById('query').value.toLowerCase().trim()))
                .map(q=>({id:q.id,name:q.players.join(' vs '),date:q.starts_at.slice(0,10)})):[],
              fixture_cards:[...document.querySelectorAll('#cards article.pick')].map(el=>({
                name:el.querySelector('.name')?.textContent,
                date:el.querySelector('.context')?.textContent.match(/Provider-listed date: (\d{4}-\d{2}-\d{2})/)?.[1],
                context:el.querySelector('.context')?.textContent||'',note:el.querySelector('.note')?.textContent||'',
                grade:el.querySelector('.grade')?.textContent,has_quote_id:el.hasAttribute('data-id'),
                has_stats:!!el.querySelector('.stat-grid'),
                projection:el.querySelectorAll('.stat-grid strong')[1]?.textContent,
                estimate:el.querySelectorAll('.stat-grid strong')[2]?.textContent})),
              cards:[...document.querySelectorAll('#cards .pick:not(article)')].map(el=>({
                id:el.dataset.id,grade:el.querySelector('.grade')?.textContent,
                projection:el.querySelectorAll('.stat-grid strong')[1]?.textContent,
                estimate:el.querySelectorAll('.stat-grid strong')[2]?.textContent})),
              game_cards:document.querySelectorAll('#cards [data-game]').length,
              empty:document.querySelector('#cards .empty')?.textContent||'',
              research_visible:['provisional-short-history','trained-short-history'].some(id=>{
                const el=document.getElementById(id);return el&&el.getClientRects().length>0;
              }),
              viewport_width:innerWidth,
              overflow:document.documentElement.scrollWidth-innerWidth
            })""",mode)
            obs['previous_league']=previous
            obs['reasons']=assess_tennis(obs)
            observations.append(obs)
    return observations

def assess_confidence(obs):
    reasons=[]
    estimates=obs.get("estimates",[])
    if any(a<b for a,b in zip(estimates,estimates[1:])):
        reasons.append("NBA_BOARD_CONFIDENCE_ORDER")
    if obs.get("viewport_width")!=390 or obs.get("overflow",0)>1:
        reasons.append("NBA_CONFIDENCE_PHONE_LAYOUT")
    if not obs.get("eligible_count"):
        # Honest no-applicable-card result, not evidence of successful correction.
        return reasons
    card=obs.get("card",{}); detail=obs.get("detail",{})
    if card.get("estimate")!=obs.get("expected_estimate") or detail.get("estimate")!=obs.get("expected_estimate"):
        reasons.append("NBA_CORRECTION_DISPLAY_MISMATCH")
    if detail.get("line")!=card.get("line") or detail.get("projection")!=card.get("projection") or detail.get("direction")!=card.get("direction"):
        reasons.append("NBA_CORRECTION_CHANGED_PICK")
    note=detail.get("note","")
    for text in (obs.get("validation_notice") or "MISSING_VALIDATION_NOTICE",
                 "Raw saved confidence "+obs.get("expected_raw", "MISSING"),
                 "Applied "+obs.get("expected_applied", "MISSING")):
        if text not in note:reasons.append("NBA_CORRECTION_PROVENANCE_MISSING")
    if obs.get("grade_before")!=obs.get("grade_after"):
        reasons.append("NBA_CORRECTION_CHANGED_GRADE")
    return list(dict.fromkeys(reasons))

def observe_confidence(page):
    page.locator('button[data-league="NBA"]').click(timeout=10000)
    page.locator('button[data-view="board"]').click(timeout=10000)
    obs=page.evaluate("""() => {
      const rows=shown(), candidates=rows.filter(p=>m.hitEstimate(p)?.confidenceCorrected);
      const p=candidates.find(p=>p.player==='Jamal Murray'&&p.stat==='AST')||candidates[0];
      const els=[...document.querySelectorAll('#cards .pick')];
      const base={eligible_count:candidates.length, viewport_width:innerWidth,
        overflow:document.documentElement.scrollWidth-innerWidth,
        estimates:els.map(e=>Number(e.querySelectorAll('.stat-grid strong')[2]?.textContent.replace(/[~%]/g,''))).filter(Number.isFinite)};
      if(!p)return {...base,scope:'NO_VISIBLE_ELIGIBLE_CORRECTION'};
      const h=m.hitEstimate(p),el=els.find(e=>e.dataset.id===m.key(p)),strong=el?.querySelectorAll('.stat-grid strong');
      return {...base,id:m.key(p),player:p.player,stat:p.stat,source_captured:h.sourceCaptured||p.confidenceCorrection.sourceCaptured,
        applied_at:h.asOf,expected_estimate:'~'+Math.round(h.rate*100)+'%',expected_raw:Math.round(h.rawRate*100)+'%',
        expected_applied:when(h.asOf),validation_notice:h.validationNotice,grade_before:p.grade,
        card:{line:strong?.[0]?.textContent,projection:strong?.[1]?.textContent,estimate:strong?.[2]?.textContent,
          direction:el?.querySelector('.chip')?.textContent.replace(/[↑↓]/g,'').trim()}};
    }""")
    if obs.get("eligible_count"):
        # CSS.escape avoids interpreting punctuation in a source-derived ID.
        selector=page.evaluate("""id => '#cards .pick[data-id="'+CSS.escape(id)+'"]'""",obs['id'])
        page.locator(selector).click(timeout=10000)
        detail=page.evaluate("""() => {
          const el=document.querySelector('#detail-content .hero'),a=el.querySelectorAll('.triple strong');
          return {line:a[0].textContent,projection:a[1].textContent,estimate:a[2].textContent,
            direction:el.querySelector('.lean').textContent.trim().split(' ')[0],note:el.querySelector('.note').textContent};
        }""")
        obs['detail']=detail
        obs['grade_after']=page.evaluate("() => state.picked.grade")
        obs['overflow']=max(obs['overflow'],page.evaluate("() => document.documentElement.scrollWidth-innerWidth"))
        page.locator('#back').click(timeout=10000)
    obs['reasons']=assess_confidence(obs)
    return obs

def assess_pace(obs):
    """Separate absent saved quotes from missing rendered pace labels."""
    reasons=[]
    if obs.get('viewport_width')!=390 or obs.get('overflow',0)>1:
        reasons.append('LIVE_PACE_PHONE_OVERFLOW')
    rows=obs.get('rows',[])
    expected=obs.get('expected_rows')
    if not isinstance(expected,int) or expected<0:
        reasons.append('LIVE_PACE_COVERAGE_NOT_TESTED')
    elif len(rows)!=expected:
        reasons.append('LIVE_PACE_PROP_RENDER_MISMATCH')
    elif expected==0 and not obs.get('empty_notice'):
        reasons.append('LIVE_PACE_EMPTY_STATE_MISSING')
    if any('Game-clock pace (estimate)' not in r.get('text','') and 'Pace unavailable:' not in r.get('text','') for r in rows):
        reasons.append('LIVE_PACE_LABEL_MISSING')
    return reasons

def observe_pace(page):
    page.locator('button[data-league="NBA"]').click(timeout=10000)
    page.locator('button[data-view="live"]').click(timeout=10000)
    target=page.evaluate("""() => {
      const g=m.currentSlateGames(state.liveGames,'NBA').find(g=>g.state==='in'&&g.fresh);
      return g?g.sport+'|'+g.gameId:null;
    }""")
    if not target:
        return {"scope":"NO_FRESH_LIVE_GAME", "reasons":[]}
    selector=page.evaluate("""id => '#cards [data-game="'+CSS.escape(id)+'"]'""",target)
    page.locator(selector).click(timeout=10000)
    obs=page.evaluate("""() => ({game:state.gamePicked.game,viewport_width:innerWidth,
      overflow:document.documentElement.scrollWidth-innerWidth,
      expected_rows:m.displayCurrentPicks(rows().filter(p=>p.gameId===state.gamePicked.gameId||p.game===state.gamePicked.game)).length,
      empty_notice:document.querySelector('#detail-content').textContent.includes('No verified pregame standard quotes were archived for this game.'),
      rows:[...document.querySelectorAll('#detail-content [data-prop]')].map(e=>({id:e.dataset.prop,text:e.textContent}))})""")
    obs['scope']='NO_SAVED_PROPS' if obs['expected_rows']==0 else 'SAVED_PROP_PACE'
    obs['reasons']=assess_pace(obs)
    page.locator('#back').click(timeout=10000)
    return obs

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
                observation["live_order"]=observe_live_order(page,sport)
                result[sport]=observation
            report=assess(result["NBA"],result["NFL"],errors,app_title=title)
            report["browser_direct_probe"]=direct
            report["live_pace"]=observe_pace(page)
            report["reasons"].extend(report["live_pace"]["reasons"])
            report["TENNIS"]=observe_tennis(page)
            report["nba_confidence"]=observe_confidence(page)
            report["reasons"].extend(report["nba_confidence"]["reasons"])
            # Keep the same context/service-worker/cache and reload as a returning
            # user does. This tests a warm reload, not an invented historical cache.
            page.reload(wait_until="domcontentloaded",timeout=45000)
            page.wait_for_function("() => typeof state !== 'undefined' && !!state.updated && !state.loading",timeout=60000)
            page.wait_for_function("() => !state.liveBusy",timeout=45000)
            report["warm_reload"]={sport:observe_live_order(page,sport) for sport in ("NBA","NFL")}
            report["tennis_warm_reload"]=observe_tennis(page)
            for phase, observations in (("FIRST_LOAD",report["TENNIS"]),("WARM_RELOAD",report["tennis_warm_reload"])):
                for obs in observations:
                    report["reasons"].extend(phase+"_"+reason for reason in obs["reasons"])
            report["cache_test_scope"]="Same-context warm reload; historical-version cache compatibility is tested offline."
            for sport in ("NBA","NFL"):
                for phase,obs in (("FIRST_LOAD",result[sport]["live_order"]),("WARM_RELOAD",report["warm_reload"][sport])):
                    report["reasons"].extend(sport+"_"+phase+"_"+reason for reason in obs["reasons"])
            if errors and "UNHANDLED_JS_ERRORS" not in report["reasons"]:
                report["reasons"].append("UNHANDLED_JS_ERRORS")
            report["browser_errors"]=errors[:10]
            if report["reasons"]:
                report["status"]="DEGRADED"
                report["browser_render_verified"]=False
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

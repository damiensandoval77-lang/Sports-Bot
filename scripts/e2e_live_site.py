"""Verify the deployed Dame's Picks app with a real mobile-size browser."""
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from mobile_board_health import board_rendered
from stalled_feed_probe import stalled_feed_deadline
from playwright.sync_api import sync_playwright

BASE=(sys.argv[1] if len(sys.argv)>1 else "https://damiensandoval77-lang.github.io/Sports-Bot").rstrip("/")
OUT=Path(sys.argv[2] if len(sys.argv)>2 else "out")
def get_bytes(path):
    req=urllib.request.Request(f"{BASE}/{path}?e2e={int(dt.datetime.now().timestamp())}",headers={"Cache-Control":"no-cache","User-Agent":"DamesPicks-ExactRelease-E2E"})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read()
def get(path):return json.loads(get_bytes(path))
def git_blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def stamp(raw):
    value=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    engine=os.environ.get("DAMES_BROWSER","chromium")
    if engine not in ("chromium","webkit"):raise ValueError("Unsupported browser engine")
    now=dt.datetime.now(dt.timezone.utc)
    expected_manifest=json.loads((Path(__file__).resolve().parents[1]/"docs/dames-picks/release.json").read_text())
    remote_manifest=get("dames-picks/release.json")
    release=remote_manifest.get("release_id")
    expected_release=expected_manifest["release_id"]
    sched=get("nba_schedule.json").get("games",[])
    saved=get("lagged_matchup_all_market_ledger.json").get("records",[])
    expected_upcoming_picks=sum(1 for r in saved if r.get("start") and now <= stamp(r["start"]) <= now + dt.timedelta(hours=24))
    recorded={(r.get("game"),stamp(r["start"])) for r in saved if r.get("start")}
    nearby=[]
    for game in sched:
        if not game.get("start") or game.get("game_state") in ("post","final"):continue
        start=stamp(game["start"])
        delta=(start-now).total_seconds()/60
        if -240<=delta<=180:
            nearby.append({"game":game.get("game"),"minutes_to_tip":round(delta),
                           "has_pick":(game.get("game"),start) in recorded})
    missing=[r for r in nearby if not r["has_pick"]]
    report={"browser":engine,"timezone":"America/New_York","checked_at":now.isoformat(),"deployed_release":release,"expected_repository_release":expected_release,"nearby_games":nearby,"checks":[]}
    def check(name,ok,details):
        report["checks"].append({"name":name,"status":"PASS" if ok else "FAIL","details":details})
    check("deployed_release_matches_repository",release==expected_release,
          {"deployed":release,"repository":expected_release})
    check("deployed_manifest_matches_repository",remote_manifest==expected_manifest,
          {"deployed_asset_pins":remote_manifest.get("asset_blob_sha1"),"repository_asset_pins":expected_manifest.get("asset_blob_sha1")})
    asset_evidence={}
    for name,expected_sha in expected_manifest.get("asset_blob_sha1",{}).items():
        try:
            actual_sha=git_blob_sha(get_bytes("dames-picks/"+name))
            asset_evidence[name]={"expected":expected_sha,"deployed":actual_sha,"exact_match":expected_sha==actual_sha}
        except Exception as error:
            asset_evidence[name]={"expected":expected_sha,"error":str(error),"exact_match":False}
    check("every_deployed_asset_matches_exact_repository_blob",bool(asset_evidence) and all(v["exact_match"] for v in asset_evidence.values()),asset_evidence)
    with sync_playwright() as browser_tool:
        browser=getattr(browser_tool,engine).launch(headless=True,**({"args":["--no-sandbox"]} if engine=="chromium" else {}))
        page=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=2,is_mobile=True,has_touch=True,timezone_id="America/New_York")
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto(f"{BASE}/dames-picks/?e2e={int(now.timestamp())}",wait_until="domcontentloaded",timeout=60000)
        page.wait_for_timeout(5000)
        if expected_upcoming_picks:
            try:
                page.wait_for_function("document.querySelectorAll('button.pick').length > 0", timeout=45000)
            except Exception:
                pass  # Record a failed rendering check and screenshot below.
        running=page.evaluate("globalThis.__damesRunningAssets || {}")
        coverage=page.evaluate("(()=>{const x=document.querySelector('#coverage');return {visible:!!x&&!x.hidden&&!!x.textContent,text:x?.textContent||''}})()")
        cards=page.locator("button.pick").count()
        footer_evidence=page.evaluate("""() => Array.from(
          document.querySelectorAll('button.pick')).map(card => {
            const footer=card.querySelector('.over-under-footer');
            const text=footer?.textContent?.replace(/\\s+/g,' ').trim() || null;
            const spans=Array.from(footer?.querySelectorAll('span') || [])
              .map(x => x.textContent.trim());
            return {player:card.querySelector('.name')?.textContent?.trim() || '',
                    footer:text, spans, has_dots:!!card.querySelector('.dots'),
                    is_exact_split:spans.length===2 &&
                      /^(?:\\d+|—) OVER$/.test(spans[0]) &&
                      /^(?:\\d+|—) UNDER$/.test(spans[1])};
          })""")
        # Fault injection against the actual deployed helper. Route only this
        # synthetic same-origin request; no provider request or data is changed.
        deadline_evidence=stalled_feed_deadline(page)
        check("deployed_stalled_feed_deadline",deadline_evidence.get("rejected") is True
              and deadline_evidence.get("error")=="Feed request timed out"
              and 80<=deadline_evidence.get("elapsed_ms",0)<3000,deadline_evidence)
        check("phone_has_no_horizontal_overflow",page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth + 1"),{"width":390})
        # Bound screenshot size even when hundreds of cards are present.
        page.screenshot(path=str(OUT/"iphone-deployed.png"),full_page=False)
        under=page.locator('button.pick').filter(has=page.locator('.chip.under'))
        if under.count():
            under.first.click()
            page.locator('#detail-content .lean.under').wait_for(timeout=10000)
            under_color=page.locator('#detail-content .lean.under').evaluate(
                "el => getComputedStyle(el).backgroundColor")
            check("under_detail_is_red",under_color=="rgb(255, 107, 122)",{"color":under_color})
            page.screenshot(path=str(OUT/"under-player-detail.png"))
            page.locator('#back').click()
        else:
            report["checks"].append({"name":"under_detail_is_red","status":"SKIP",
                                     "details":{"reason":"No authentic Under card available"}})
        detail_evidence=[]
        for sport in ("NBA","NFL"):
            page.locator('[data-view="tracker"]').click()
            page.locator('[data-league="'+sport+'"]').click()
            try:
                page.locator('button.pick').first.wait_for(timeout=15000)
                page.locator('button.pick').first.click()
                page.locator('#detail:not(.hidden)').wait_for(timeout=10000)
                evidence=page.evaluate("""() => {
                    const hero=document.querySelector('#detail-content .hero');
                    return {player:document.querySelector('#player')?.textContent,
                            projection:!!hero, take_immediately_after_projection:
                            !!hero?.nextElementSibling?.classList.contains('take')};
                }""")
                detail_evidence.append({"sport":sport,**evidence})
                page.screenshot(path=str(OUT/(sport.lower()+"-player-detail.png")))
                page.locator('#back').click()
                check(sport.lower()+"_player_detail_and_take",bool(evidence.get("projection"))
                      and bool(evidence.get("take_immediately_after_projection")),evidence)
            except Exception as error:
                check(sport.lower()+"_player_detail_and_take",False,{"error":str(error)[:400]})
                if page.locator('#back').is_visible():page.locator('#back').click()
            page.locator('[data-view="live"]').click()
            game_count=page.locator('[data-game]').count()
            if game_count:
                page.locator('[data-game]').first.click()
                text=page.locator('#detail-content').inner_text()
                check(sport.lower()+"_game_detail",'Full published player box score' in text,
                      {"games":game_count,"boxscore_section":'Full published player box score' in text})
                page.screenshot(path=str(OUT/(sport.lower()+"-game-detail.png")))
                page.locator('#back').click()
            else:
                check(sport.lower()+"_game_detail",False,{"games":0})
        browser.close()
    footer_details={"visible_board_cards":cards,"cards":footer_evidence[:12]}
    if cards:
        check("live_board_footer_over_under_only",
              len(footer_evidence)==cards and
              all(x["is_exact_split"] and not x["has_dots"] and
                  x["footer"] in (" ".join(x["spans"]), "".join(x["spans"]))
                  for x in footer_evidence),
              footer_details)
    else:
        report["checks"].append({"name":"live_board_footer_over_under_only",
                                 "status":"SKIP","details":footer_details})
    check("executing_assets_match_repository_release",bool(running) and all(running.get(name)==expected_release for name in ("feeds.js","live_direct.js","dames_take.js","provisional.js","short_history.js")),running)
    check("no_browser_javascript_exceptions",not errors,errors[:8])
    check("board_cards_or_honest_empty_state",board_rendered(cards, expected_upcoming_picks),{"cards":cards,"nearby_games":len(nearby),"expected_upcoming_picks":expected_upcoming_picks})
    check("near_tip_saved_picks",not [g for g in missing if g["minutes_to_tip"]<=60],missing)
    check("missing_games_disclosed",not missing or coverage["visible"],coverage)
    report["overall"]="FAIL" if any(c["status"]=="FAIL" for c in report["checks"]) else "PASS"
    (OUT/"iphone-deployed.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 1 if report["overall"]=="FAIL" else 0
if __name__=="__main__":raise SystemExit(main())

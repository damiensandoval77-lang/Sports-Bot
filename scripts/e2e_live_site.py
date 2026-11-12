"""Verify the deployed Dame's Picks app with a real mobile-size browser."""
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
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
    now=dt.datetime.now(dt.timezone.utc)
    expected_manifest=json.loads((Path(__file__).resolve().parents[1]/"docs/dames-picks/release.json").read_text())
    remote_manifest=get("dames-picks/release.json")
    release=remote_manifest.get("release_id")
    expected_release=expected_manifest["release_id"]
    sched=get("nba_schedule.json").get("games",[])
    saved=get("lagged_matchup_all_market_ledger.json").get("records",[])
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
    report={"checked_at":now.isoformat(),"deployed_release":release,"expected_repository_release":expected_release,"nearby_games":nearby,"checks":[]}
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
    browser_evidence={}
    with sync_playwright() as browser_tool:
        # Both mobile Chromium and mobile-size WebKit (Safari rendering engine)
        # are checked. These are emulations, not a physical iPhone device.
        for engine in ("chromium","webkit"):
            browser=None
            try:
                browser=getattr(browser_tool,engine).launch(
                    headless=True,args=["--no-sandbox"] if engine=="chromium" else [])
                page=browser.new_page(viewport={"width":390,"height":844},
                    device_scale_factor=3,is_mobile=True,has_touch=True)
                errors=[]
                page.on("pageerror",lambda error:errors.append(str(error)))
                page.goto(f"{BASE}/dames-picks/?e2e={int(now.timestamp())}",
                    wait_until="domcontentloaded",timeout=60000)
                page.wait_for_timeout(5000)
                running=page.evaluate("globalThis.__damesRunningAssets || {}")
                coverage=page.evaluate("""(()=>{
                  const x=document.querySelector('#coverage');
                  return {visible:!!x&&!x.hidden&&!!x.textContent,
                          text:x?.textContent||''}})()""")
                cards=page.locator("button.pick").count()
                overflow=page.evaluate("document.documentElement.scrollWidth > window.innerWidth+2")
                detail_ok=None
                if cards:
                    page.locator("button.pick").first.click()
                    detail_ok=page.locator("#detail").is_visible() and bool(page.locator("#player").inner_text().strip())
                    page.locator("#back").click()
                    detail_ok=detail_ok and page.locator("#board").is_visible()
                page.screenshot(path=str(OUT/f"iphone-{engine}-deployed.png"),full_page=True)
                browser_evidence[engine]={"running":running,"coverage":coverage,
                  "cards":cards,"javascript_errors":errors[:8],
                  "horizontal_overflow":overflow,"card_detail_navigation":detail_ok}
            except Exception as error:
                browser_evidence[engine]={"error":str(error)}
            finally:
                if browser:browser.close()
    for engine,evidence in browser_evidence.items():
        running=evidence.get("running") or {}
        check(engine+"_executing_assets_match_release",
            bool(running) and all(running.get(name)==expected_release
            for name in ("feeds.js","live_direct.js","dames_take.js")),running)
        check(engine+"_no_javascript_exceptions",not evidence.get("error")
              and not evidence.get("javascript_errors"),
              evidence.get("javascript_errors") or evidence.get("error"))
        check(engine+"_iPhone_390px_no_horizontal_overflow",
              evidence.get("horizontal_overflow") is False,
              evidence.get("horizontal_overflow",evidence.get("error")))
        check(engine+"_player_card_opens_and_returns",
              evidence.get("card_detail_navigation") is not False,
              {"cards":evidence.get("cards"),"detail_ok":evidence.get("card_detail_navigation")})
        check(engine+"_board_or_honest_empty_state",
              (evidence.get("cards",0)>0 or not nearby or bool(missing))
                and not evidence.get("error"),
              {"cards":evidence.get("cards"),"nearby_games":len(nearby)})
        check(engine+"_missing_games_disclosed",
              not missing or bool((evidence.get("coverage") or {}).get("visible")),
              evidence.get("coverage") or evidence.get("error"))
    check("near_tip_saved_picks",not [g for g in missing if g["minutes_to_tip"]<=60],missing)
    report["overall"]="FAIL" if any(c["status"]=="FAIL" for c in report["checks"]) else "PASS"
    (OUT/"iphone-deployed.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 1 if report["overall"]=="FAIL" else 0
if __name__=="__main__":raise SystemExit(main())

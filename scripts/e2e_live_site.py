"""Verify the deployed Dame's Picks app with a real mobile-size browser."""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=(sys.argv[1] if len(sys.argv)>1 else "https://damiensandoval77-lang.github.io/Sports-Bot").rstrip("/")
OUT=Path(sys.argv[2] if len(sys.argv)>2 else "out")
def get(path):
    req=urllib.request.Request(f"{BASE}/{path}?e2e={int(dt.datetime.now().timestamp())}",headers={"Cache-Control":"no-cache"})
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read())
def stamp(raw):
    value=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    now=dt.datetime.now(dt.timezone.utc)
    release=get("dames-picks/release.json")["release_id"]
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
    report={"checked_at":now.isoformat(),"deployed_release":release,"nearby_games":nearby,"checks":[]}
    def check(name,ok,details):
        report["checks"].append({"name":name,"status":"PASS" if ok else "FAIL","details":details})
    with sync_playwright() as browser_tool:
        browser=browser_tool.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=3,is_mobile=True,has_touch=True)
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto(f"{BASE}/dames-picks/?e2e={int(now.timestamp())}",wait_until="domcontentloaded",timeout=60000)
        page.wait_for_timeout(5000)
        running=page.evaluate("globalThis.__damesRunningAssets || {}")
        coverage=page.evaluate("(()=>{const x=document.querySelector('#coverage');return {visible:!!x&&!x.hidden&&!!x.textContent,text:x?.textContent||''}})()")
        cards=page.locator("button.pick").count()
        page.screenshot(path=str(OUT/"iphone-deployed.png"),full_page=True)
        browser.close()
    check("released_assets_match_deployed_manifest",bool(running) and all(v==release for v in running.values()),running)
    check("no_browser_javascript_exceptions",not errors,errors[:8])
    check("board_cards_or_honest_empty_state",cards>0 or not nearby or bool(missing),{"cards":cards,"nearby_games":len(nearby)})
    check("near_tip_saved_picks",not [g for g in missing if g["minutes_to_tip"]<=60],missing)
    check("missing_games_disclosed",not missing or coverage["visible"],coverage)
    report["overall"]="FAIL" if any(c["status"]=="FAIL" for c in report["checks"]) else "PASS"
    (OUT/"iphone-deployed.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 1 if report["overall"]=="FAIL" else 0
if __name__=="__main__":raise SystemExit(main())

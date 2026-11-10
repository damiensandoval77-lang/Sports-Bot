"""Real iPhone browser smoke test: pretip archived quotes survive into live cards.

Runs only on started games with source-verified archived lines, never fetches
paid provider endpoints or invents market outcomes.
"""
import datetime as dt
import json
import os
import sys
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/live_pregame_line_probe.json"
SITE=os.environ.get("SPORTS_BOT_PUBLIC_SITE_URL","https://damiensandoval77-lang.github.io/Sports-Bot/")

def key(s):
    text=unicodedata.normalize("NFKD",str(s or "")).casefold()
    return "".join(c for c in text if c.isalnum() and not unicodedata.combining(c))

def run():
    from playwright.sync_api import sync_playwright
    now=dt.datetime.now(dt.timezone.utc)
    archive=json.loads((ROOT/"docs/prizepicks_pregame_line_archive.json").read_text())
    out={"checked_at":now.isoformat(),"status":"NOT_VERIFIED",
         "source_archive_count":len(archive.get("quotes") or []),"checks":[],
         "errors":[],"public_site":SITE}
    grouped={}
    for q in archive.get("quotes") or []:
        try:
            start=dt.datetime.fromisoformat(q["starts_at"].replace("Z","+00:00"))
            if not 0<=(now-start).total_seconds()<=5*3600:continue
            ident=(key(q["player"]),q["team"],q["stat"])
            grouped.setdefault(q["game"],set()).add(ident)
        except (ValueError,KeyError,TypeError):continue
    if not grouped:
        out.update(status="NO_RECENT_STARTED_GAMES",note="No started matchups with independently archived lines to check.")
        return out
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":390,"height":844},
                                  timezone_id="America/New_York")
            page.on("pageerror",lambda e:out["errors"].append("JS:"+str(e)[:180]))
            response=page.goto(SITE,wait_until="domcontentloaded",timeout=50000)
            if not response or response.status!=200:raise RuntimeError("Public site not HTTP 200")
            page.wait_for_selector("#game-strip button.score-tile",timeout=35000)
            for game,markets in sorted(grouped.items(),key=lambda kv:-len(kv[1])):
                tile=next((t for t in page.locator("#game-strip button.score-tile").all()
                           if game in str(t.get_attribute("aria-label") or "")),None)
                if not tile:
                    out["checks"].append({"game":game,"status":"GAME_TILE_MISSING"})
                    continue
                # Old game's already-rendered cards can otherwise satisfy
                # the wait immediately after a different tab is clicked.
                tile.click(timeout=6000)
                try:
                    page.wait_for_function(
                        """game => document.querySelector('#live-prop-title')?.textContent === game &&
                        !document.querySelector('#live-prop-context')?.textContent?.includes('Checking for updated player totals') &&
                        document.querySelectorAll('#live-prop-cards .live-prop-card').length > 0""",
                        arg=game,timeout=35000)
                except Exception:
                    out["checks"].append({"game":game,"status":"NO_LIVE_TRACKER_CARDS",
                                          "context":page.locator("#live-prop-context").inner_text()[:220]})
                    continue
                cards=page.locator("#live-prop-cards .live-prop-card").evaluate_all(
                    """nodes => nodes.map(n=>({
                        name:n.querySelector('.live-name')?.textContent||'',
                        label:n.querySelector('.live-stat')?.textContent||'',
                        line:[...n.querySelectorAll('.live-prop-values b')][2]?.textContent||''
                    }))""")
                covered=set()
                for q in markets:
                    player,team,stat=q
                    if any(key(r["name"])==player and team in r["label"] and
                           stat in r["label"] and
                           r["line"] not in ("","Not available","Not captured","—")
                           for r in cards):
                        covered.add(q)
                ratio=len(covered)/len(markets) if markets else 0
                out["checks"].append({"game":game,"status":"COVERED" if ratio>=.9 else "MISSING_SAVED_LINES",
                    "expected_unique_markets":len(markets),"shown_with_lines":len(covered),
                    "coverage_fraction":round(ratio,3),"rendered_cards":len(cards)})
            out["status"]="READY" if len(out["checks"])==len(grouped) and all(
                x["status"]=="COVERED" for x in out["checks"]) and not out["errors"] else "DEGRADED"
        finally:
            browser.close()
    return out

def main():
    try:report=run()
    except Exception as exc:
        report={"status":"DEGRADED","checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                "errors":[type(exc).__name__+":"+str(exc)[:240]],"checks":[]}
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print("LIVE PREGAME LINE BROWSER CHECK",json.dumps(report))
    return 1 if report["status"]=="DEGRADED" else 0

if __name__=="__main__":sys.exit(main())

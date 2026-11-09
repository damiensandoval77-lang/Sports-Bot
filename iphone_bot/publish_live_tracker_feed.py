"""Publish verified ESPN player stats for live-tracker browser fallback.

The client attempts ESPN live every 45s. This no-cost, time-stamped backup
supports browsers where ESPN direct requests fail. Never claims 45s freshness,
never stores model forecasts, and never invents player totals.
"""
import json
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from .capture_live_research import players,matchup
except ImportError:
    from capture_live_research import players,matchup

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/live_player_tracking.json"
BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
ET=ZoneInfo("America/New_York")

def get(path):
    req=urllib.request.Request(BASE+path,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=18) as response:return json.load(response)

def build(now,scoreboard,summaries):
    data={"status":"OBSERVED_ESPN_LIVE_BOX_SCORES_SERVER_FALLBACK",
          "captured_at":now.isoformat(),
          "date_eastern":now.astimezone(ET).date().isoformat(),
          "source":"ESPN game scoreboard + exact verified game summary",
          "games":[],"errors":[],"player_totals_are_observations":True,
          "not_live_sportsbook_odds":True,"not_ai_predictions":True}
    for event in scoreboard.get("events",[]):
        state=event.get("status",{}).get("type",{}).get("state")
        if state not in ("in","post"):continue
        event_id=str(event.get("id",""))
        if not event_id.isdecimal():continue
        comp=event.get("competitions",[])
        expected=matchup(comp[0].get("competitors",[])) if comp else None
        summary=summaries.get(event_id)
        if not expected or not summary:
            data["errors"].append({"event_id":event_id,"reason":"MISSING_SOURCE"})
            continue
        headers=summary.get("header",{}).get("competitions",[])
        if not headers or matchup(headers[0].get("competitors",[]))!=expected:
            data["errors"].append({"event_id":event_id,"reason":"DIFFERENT_GAME"})
            continue
        rows=players(summary)
        if not rows:
            data["errors"].append({"event_id":event_id,"reason":"NO_VERIFIED_STATS"})
            continue
        status=event["status"]
        data["games"].append({"game":expected,"event_id":event_id,
            "state":state,"period":status.get("period"),
            "displayClock":status.get("displayClock"),
            "clock":status.get("clock"),
            "shortDetail":status.get("type",{}).get("shortDetail"),
            "player_rows":rows})
    return data

def main():
    now=datetime.now(timezone.utc)
    date=now.astimezone(ET).strftime("%Y%m%d")
    board=get("/scoreboard?dates="+date+"&limit=100")
    summaries={}
    for event in board.get("events",[]):
        if event.get("status",{}).get("type",{}).get("state") not in ("in","post"):continue
        ident=str(event.get("id",""))
        if not ident.isdecimal():continue
        try:summaries[ident]=get("/summary?event="+ident)
        except Exception as error:print("Summary unavailable",ident,type(error).__name__)
    data=build(now,board,summaries)
    active=[]
    for event in board.get("events",[]):
        if event.get("status",{}).get("type",{}).get("state")!="in":
            continue
        comps=event.get("competitions",[])
        game=matchup(comps[0].get("competitors",[])) if comps else None
        if game:active.append(game)
    captured={g["game"] for g in data["games"] if g["state"]=="in"}
    missing=sorted(set(active)-captured)
    print("LIVE TRACKER COVERAGE:",
          json.dumps({"active_matchups":active,"observed_active_matchups":sorted(captured),
                      "missing_active_matchups":missing},sort_keys=True),flush=True)
    if missing:
        raise RuntimeError("Active NBA matchups lack verified live player totals: "+
                           ", ".join(missing))
    if data["games"]:
        OUTPUT.write_text(json.dumps(data,separators=(",",":"),ensure_ascii=False)+"\n")
    print("ESPN LIVE FALLBACK:",len(data["games"]),"games",
          sum(len(g["player_rows"]) for g in data["games"]),
          "verified player rows, errors",len(data["errors"]),
          "published",bool(data["games"]))
    if not data["games"] and any(e.get("status",{}).get("type",{}).get("state")=="in" for e in board.get("events",[])):
        raise RuntimeError("Active ESPN games exist but no verified player rows were available")

if __name__=="__main__":main()

"""Publish verified ESPN player stats for live-tracker browser fallback.

The client attempts ESPN live every 45s. This no-cost, time-stamped backup
supports browsers where ESPN direct requests fail. Never claims 45s freshness,
never stores model forecasts, and never invents player totals.
"""
import json
import urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from .capture_live_research import players,matchup,get as fetch_espn
except ImportError:
    from capture_live_research import players,matchup,get as fetch_espn

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/live_player_tracking.json"
BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
ET=ZoneInfo("America/New_York")

def get(path):
    # Share JSON validation / retry behavior with immutable research capture.
    # A broken ESPN scoreboard must not overwrite the last verified snapshot.
    return fetch_espn(path)

def build(now,scoreboard,summaries,previous=None):
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
            "player_rows":rows,"observed_at":now.isoformat(),"stale":False})
    active={}
    for event in scoreboard.get("events",[]):
        if event.get("status",{}).get("type",{}).get("state")!="in":continue
        comps=event.get("competitions",[])
        name=matchup(comps[0].get("competitors",[])) if comps else None
        ident=str(event.get("id",""))
        if name and ident.isdecimal():active[name]=ident
    observed={g["game"] for g in data["games"] if g["state"]=="in"}
    missing=sorted(set(active)-observed)
    old=previous or {}
    if old.get("date_eastern")==data["date_eastern"] and old.get("status")==data["status"]:
        current={str(g["event_id"]) for g in data["games"]}
        for prior in old.get("games",[]):
            ident=str(prior.get("event_id",""))
            stamp=prior.get("observed_at") or old.get("captured_at")
            try:age=now-datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
            except (ValueError,TypeError):continue
            if age<timedelta(0) or age>timedelta(minutes=30):continue
            name=prior.get("game")
            if name in missing and ident==active[name] and ident not in current:
                data["games"].append({**prior,"observed_at":stamp,"stale":True})
                current.add(ident)
    data["coverage"]={"active_matchups":sorted(active),
        "fresh_active_matchups":sorted(observed),
        "missing_fresh_matchups":missing,
        "retained_stale_matchups":sorted(g["game"] for g in data["games"] if g.get("stale")),
        "complete":not missing}
    data["coverage_status"]="COMPLETE" if not missing else "PARTIAL_LIVE_DATA"
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
    previous={}
    if OUTPUT.exists():
        try:previous=json.loads(OUTPUT.read_text())
        except (OSError,ValueError):pass
    data=build(now,board,summaries,previous)
    print("LIVE TRACKER COVERAGE:",json.dumps(data["coverage"],sort_keys=True),flush=True)
    # Publish data even when one game is missing; never let the dashboard
    # confuse retained observations with current player totals.
    OUTPUT.write_text(json.dumps(data,separators=(",",":"),ensure_ascii=False)+"\n")
    print("ESPN LIVE FALLBACK:",len(data["games"]),"games",
          sum(len(g["player_rows"]) for g in data["games"]),
          "verified player rows, errors",len(data["errors"]),
          "coverage",data["coverage_status"],flush=True)

if __name__=="__main__":main()

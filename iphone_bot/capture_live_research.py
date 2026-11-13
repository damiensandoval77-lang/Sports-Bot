"""Capture timestamped, immutable NBA in-game player boxscore snapshots.

Public ESPN data (no sportsbook API credits). Results are OBSERVATIONS, not
post-tip forecasts. Does not backfill missed live periods or overwrite data.
"""
import gzip
import json
import re
import urllib.request
import time
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/research_live"
ET=ZoneInfo("America/New_York")
BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

def get(path):
    """Require actual ESPN JSON; retry transient HTML/empty responses.

    On continued failure callers must preserve saved observations. Never
    reinterpret an HTML interstitial as an empty active scoreboard.
    """
    req=urllib.request.Request(BASE+path,headers={
        "User-Agent":"Mozilla/5.0",
        "Accept":"application/json"})
    last_error=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=18) as response:
                raw=response.read(4_000_001)
                content_type=response.headers.get("Content-Type","").lower()
            if len(raw)>4_000_000:
                raise ValueError("ESPN_JSON_RESPONSE_TOO_LARGE")
            if not raw or "html" in content_type or raw.lstrip().startswith(b"<"):
                raise ValueError("ESPN_RETURNED_NON_JSON")
            parsed=json.loads(raw)
            if not isinstance(parsed,dict):
                raise ValueError("ESPN_RESPONSE_NOT_OBJECT")
            return parsed
        except (OSError,ValueError,json.JSONDecodeError) as exc:
            last_error=exc
            if attempt<2:time.sleep(0.5*(attempt+1))
    raise RuntimeError("ESPN_JSON_FETCH_FAILED after 3 attempts: "+
                       type(last_error).__name__+"; prior observations preserved") from last_error

def matchup(competitors):
    if not isinstance(competitors,list):return None
    sides={c.get("homeAway"):c.get("team",{}).get("displayName") for c in competitors}
    if not sides.get("home") or not sides.get("away"):return None
    return sides["away"]+" @ "+sides["home"]

def stat_value(value):
    s=str(value).strip()
    if not re.fullmatch(r"(?:\d+)(?:\.\d+)?",s):return None
    value=float(s)
    return int(value) if value.is_integer() else value

def players(summary):
    out=[]
    for group in summary.get("boxscore",{}).get("players",[]):
        team=group.get("team",{}).get("abbreviation")
        if not team:continue
        for block in group.get("statistics",[]):
            labels=block.get("labels") or block.get("names") or []
            lookup={str(v).upper():i for i,v in enumerate(labels)}
            if not all(m in lookup for m in ("PTS","REB","AST")):continue
            for a in block.get("athletes",[]):
                if a.get("didNotPlay") or a.get("didNotDress"):continue
                athlete=a.get("athlete",{})
                values=a.get("stats",[])
                if not athlete.get("displayName") or not isinstance(values,list):continue
                try:
                    pts,reb,ast=[stat_value(values[lookup[x]]) for x in ("PTS","REB","AST")]
                except (IndexError,TypeError):continue
                if any(x is None for x in (pts,reb,ast)):continue
                out.append({"player_id":str(athlete.get("id","")),
                    "player":athlete["displayName"],"team":team,
                    "PTS":pts,"REB":reb,"AST":ast,"PRA":pts+reb+ast})
    return out

def capture(now,scoreboard,summary_by_id):
    day=now.astimezone(ET).date().isoformat()
    output={"status":"OBSERVED_LIVE_PLAYER_TOTALS_NOT_PREGAME_PICKS",
      "source":"ESPN live player boxscore",
      "captured_at":now.isoformat(),"date_eastern":day,
      "games":[],"errors":[],"live_data_changes_over_time":True,
      "no_betting_odds_or_model_predictions_modified":True}
    for event in scoreboard.get("events",[]):
        if event.get("status",{}).get("type",{}).get("state")!="in":continue
        event_id=str(event.get("id",""))
        if not event_id.isdecimal():continue
        competition=event.get("competitions",[{}])[0]
        name=matchup(competition.get("competitors",[]))
        if not name:continue
        if event_id not in summary_by_id:
            output["errors"].append({"game_id":event_id,"reason":"NO_VALID_SUMMARY"})
            continue
        summary=summary_by_id[event_id]
        headers=summary.get("header",{}).get("competitions",[])
        if not headers or matchup(headers[0].get("competitors",[]))!=name:
            output["errors"].append({"game_id":event_id,"reason":"MATCHUP_MISMATCH"})
            continue
        stats=players(summary)
        if not stats:
            output["errors"].append({"game_id":event_id,"reason":"NO_PLAYER_BOX_STATS"})
            continue
        status=event["status"]
        output["games"].append({"espn_event_id":event_id,"game":name,
            "period":status.get("period"),"clock":status.get("displayClock"),
            "player_rows":stats})
    return output

def save(output,root):
    if not output["games"]:return None
    at=datetime.fromisoformat(output["captured_at"])
    folder=Path(root)/output["date_eastern"]
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(at.strftime("%Y%m%dT%H%M%SZ")+".json.gz")
    raw=json.dumps(output,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    if path.exists():
        if gzip.decompress(path.read_bytes())!=raw:
            raise RuntimeError("Live checkpoint collision; existing data cannot be overwritten")
        return path
    path.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
    return path

def main():
    now=datetime.now(timezone.utc)
    day=now.astimezone(ET).strftime("%Y%m%d")
    board=get("/scoreboard?dates="+day+"&limit=100")
    summaries={}
    errors={}
    for event in board.get("events",[]):
        if event.get("status",{}).get("type",{}).get("state")!="in":continue
        event_id=str(event.get("id",""))
        if not event_id.isdecimal():continue
        try:summaries[event_id]=get("/summary?event="+event_id)
        except Exception as exc:errors[event_id]=str(exc)
    report=capture(now,board,summaries)
    report["errors"].extend({"game_id":k,"reason":"ESPN_SUMMARY_FETCH_FAILED",
                             "error":v[:120]} for k,v in errors.items())
    result=save(report,OUTPUT)
    print("LIVE RESEARCH CHECKPOINT:",result.relative_to(ROOT) if result else "NO_ACTIVE_PLAYER_STATS",
          "games",len(report["games"]),"player rows",
          sum(len(g["player_rows"]) for g in report["games"]),
          "errors",len(report["errors"]))
    if errors and not result:raise RuntimeError("Live ESPN data collection failed without usable observations")

if __name__=="__main__":main()

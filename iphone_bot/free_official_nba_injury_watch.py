"""Free official NBA report change detector; keyless and source-verified.

This detector runs AFTER fetch_official_injuries.py. It never promotes an
unverified ESPN fallback to official. Only a status *transition* for the
same player, game date and team is actionable. An older or inaccessible
report cannot replace a verified newer one. Keep a pretip audit trail of
changes until games end, without inventing a first-seen OUT transition.
"""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
CURRENT=ROOT/"docs/injury_context.json"
PREVIOUS=ROOT/"docs/free_nba_injury_watch.json"
ET=ZoneInfo("America/New_York")

def timestamp(text):
    v=datetime.fromisoformat(str(text).replace("Z","+00:00"))
    if v.tzinfo is None:raise ValueError("Timestamp must include timezone")
    return v.astimezone(timezone.utc)

def official_rows(source):
    if (source.get("status")!="OFFICIAL_NBA_REPORT_VERIFIED" or
        source.get("injury_data_verified") is not True):return None
    issued=timestamp(source["report_issued_at"])
    rows={}
    for row in source.get("players",[]):
        pid=str(row.get("player_id") or "")
        team=str(row.get("team") or "")
        day=str(row.get("game_date") or "")
        status=str(row.get("status") or "").upper()
        if not pid.isdigit() or len(team)!=3 or len(day)!=10 or status not in (
            "OUT","AVAILABLE","QUESTIONABLE","DOUBTFUL","PROBABLE"):continue
        k=(pid,team,day)
        if k in rows and rows[k]["status"]!=status:
            rows[k]={"player_id":pid,"team":team,"game_date":day,"status":"CONFLICTING"}
            continue
        rows[k]={"player_id":pid,"team":team,"game_date":day,"player":row.get("player",""),
                 "status":status}
    return issued,rows

def update(previous,current,now):
    now=timestamp(now.isoformat()) if isinstance(now,datetime) else timestamp(now)
    newest=official_rows(current)
    older=official_rows(previous.get("report",{}))
    last_events=previous.get("events",[])
    events=[e for e in last_events if isinstance(e,dict) and e.get("status")=="OUT"
         and e.get("source")=="OFFICIAL_NBA_REPORT"
         and e.get("date_eastern") and e.get("reported_at")
         and now-timestamp(e["reported_at"])<timedelta(hours=12)
         and now.date()<=datetime.fromisoformat(e["date_eastern"]).date()+timedelta(days=1)]
    if not newest:return previous,False,"NO_VERIFIED_OFFICIAL_UPDATE"
    issued,rows=newest
    if issued>now or (now-issued)>timedelta(hours=18):
        return previous,False,"STALE_OR_FUTURE_OFFICIAL_UPDATE"
    if older and issued<=older[0]:
        return previous,False,"UNCHANGED_OR_OLDER_REPORT"
    changes=[]
    if older:
        prev=older[1]
        for k,v in rows.items():
            old=prev.get(k)
            # Do not infer player availability from absence in an earlier PDF.
            if not old or old["status"]=="CONFLICTING" or v["status"]=="CONFLICTING":
                continue
            if old["status"]!=v["status"]:
                changes.append({**v,"previous_status":old["status"],
                    "reported_at":issued.isoformat(),"date_eastern":v["game_date"],
                    "source":"OFFICIAL_NBA_REPORT","official":True})
    for change in changes:
        k=(change["player_id"],change["team"],change["game_date"])
        events=[x for x in events if (x.get("player_id"),x.get("team"),x.get("game_date"))!=k]
        if change["status"]=="OUT":events.append(change)
    status=sorted(rows.values(),key=lambda x:(x["game_date"],x["team"],x["player_id"]))
    result={"status":"FREE_OFFICIAL_NBA_INJURY_MONITOR",
      "last_checked_at":now.isoformat(),"report_issued_at":issued.isoformat(),
      "report":current,"players":status,
      "events":sorted(events,key=lambda x:(x["game_date"],x["team"],x["player_id"])),
      "new_changes":changes,
      "official_confirmed":True,"requires_paid_api":False}
    return result,True,"NEW_OFFICIAL_REPORT"

def main():
    now=datetime.now(timezone.utc)
    current=json.loads(CURRENT.read_text()) if CURRENT.exists() else {}
    previous=json.loads(PREVIOUS.read_text()) if PREVIOUS.exists() else {}
    payload,changed,reason=update(previous,current,now)
    # First successful report seeds a baseline without making up OUT changes.
    if changed:PREVIOUS.write_text(json.dumps(payload,indent=2)+"\n")
    print("FREE_NBA_INJURY_MONITOR",json.dumps({
       "status":reason,"changed":changed,
       "new_out_transitions":sum(e["status"]=="OUT" for e in payload.get("new_changes",[])),
       "tracked_recent_out_events":len(payload.get("events",[]))}),flush=True)

if __name__=="__main__":main()

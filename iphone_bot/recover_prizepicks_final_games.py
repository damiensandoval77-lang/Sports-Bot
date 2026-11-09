"""Recover final verified player boxes for outstanding pretip PrizePicks research.

Game discovery is restricted to PENDING previously saved records, dated within
the last 3 Eastern days. Actual outcomes require final NBA/ESPN boxscores.
Never turns an AI forecast into a boxscore or makes a paid odds request.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from iphone_bot.fetch_final_boxscores import gather
from iphone_bot.prizepicks_research_ledger import LEDGER, ROOT, utc

OUT=ROOT/"data/nba/current/prizepicks_verified_final_games.json"
STATUS=ROOT/"docs/prizepicks_final_recovery_status.json"
ET=ZoneInfo("America/New_York")

def pending_matchup_requests(records,now=None,max_matchups=12,days_back=3):
    now=now or dt.datetime.now(dt.timezone.utc)
    minimum=(now.astimezone(ET).date()-dt.timedelta(days=days_back)).isoformat()
    matchups={}
    for r in records:
        if r.get("status")!="PENDING":continue
        start=utc(r.get("start"))
        if start is None or (now-start).total_seconds()<4*3600:continue
        date=start.astimezone(ET).date().isoformat()
        if date<minimum or not r.get("game") or not r.get("team"):continue
        key=(date,r["game"])
        matchups.setdefault(key,{"status":"PENDING","event_start":r["start"],
                                  "game":r["game"],"team":r["team"],
                                  "player_id":str(r.get("player_id") or "")})
    if len(matchups)>max_matchups:
        # Fail closed: never falsely claim a complete recovery if over budget.
        raise ValueError("Pending finals exceed safe per-run matchup cap")
    return list(matchups.values())

def recover(records,now=None,request=None):
    pending=pending_matchup_requests(records,now=now)
    if not pending:
        return [],{"status":"NO_ELIGIBLE_RECENT_PRIZEPICKS_PENDING_GAMES",
                   "requested_matchups":0,"verified_rows":0,"errors":[]}
    if request is None:
        found,report=gather(pending,now=now)
    else:
        found,report=gather(pending,now=now,request=request)
    seen=set()
    verified=[]
    for row in found:
        if row.get("final_confirmed") is not True or row.get("dnp_final_verified"):
            continue
        if row.get("source") not in ("NBA_CDN_FINAL","ESPN_FINAL"):
            continue
        ident=(row.get("source_game_id"),row.get("player"),row.get("team"),row.get("date"))
        if ident in seen:continue
        seen.add(ident)
        verified.append(row)
    report["requested_matchups"]=len(pending)
    report["verified_rows"]=len(verified)
    report["recovery_source"]="VERIFIED_FINAL_BOXSCORES_ONLY"
    return verified,report

def main():
    records=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    try:
        rows,report=recover(records)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as e:
        rows=[]
        report={"status":"PRIZEPICKS_FINAL_RECOVERY_FAILED","requested_matchups":None,
                "verified_rows":0,"errors":[type(e).__name__]}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(rows,indent=2)+"\n")
    STATUS.write_text(json.dumps({**report,
        "checked_at":dt.datetime.now(dt.timezone.utc).isoformat()},indent=2)+"\n")
    print("PrizePicks verified final recovery:",json.dumps({
        "status":report["status"],"requested_matchups":report["requested_matchups"],
        "verified_rows":len(rows),"errors":len(report.get("errors",[]))}))
    if report["status"]=="PRIZEPICKS_FINAL_RECOVERY_FAILED":
        raise SystemExit(1)

if __name__=="__main__":
    main()

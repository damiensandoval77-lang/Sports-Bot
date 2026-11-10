"""Public, read-only ESPN NFL live player boxscore snapshot.

Writes a separate live_2026.json. Never modifies frozen picks or finalized
nflverse grades. Fail safely and retain prior non-stale snapshot on HTTP errors.
"""
import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"docs/nfl/data"
SCOREBOARD="https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date}&limit=100"
SUMMARY="https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event}"
STAT_KEYS={
 "passing":{"YDS":"PASS_YDS","TD":"PASS_TD","INT":"PASS_INT","C/ATT":"PASS_CMP_ATT"},
 "rushing":{"YDS":"RUSH_YDS","CAR":"RUSH_ATT","ATT":"RUSH_ATT","TD":"RUSH_TD"},
 "receiving":{"YDS":"REC_YDS","REC":"REC","TGTS":"TGT","TAR":"TGT","TD":"REC_TD"}
}
def load(url):
    req=Request(url,headers={"User-Agent":"NFLResearchBot/1.0 (public scoreboard data)","Accept":"application/json"})
    with urlopen(req,timeout=15) as rsp:return json.load(rsp)

def num(value):
    try:
        if value is None or str(value).strip() in ("","--","-"):return None
        v=float(str(value).replace(",",""))
        return v if v==v and abs(v)!=float("inf") else None
    except (ValueError,TypeError):return None

def parse_summary(payload,away,home):
    players={}
    for side in (payload.get("boxscore") or {}).get("players",[]):
        team=(side.get("team") or {}).get("abbreviation","").upper()
        if team not in (away,home):continue
        for statgroup in side.get("statistics",[]):
            group=str(statgroup.get("name","")).lower()
            mapper=STAT_KEYS.get(group)
            if not mapper:continue
            labels=statgroup.get("labels",[])
            for entry in statgroup.get("athletes",[]):
                athlete=entry.get("athlete") or {}
                name=athlete.get("displayName") or athlete.get("fullName")
                aid=str(athlete.get("id") or "")
                if not name or not aid:continue
                key=(team,aid)
                record=players.setdefault(key,{"player":name,"team":team,"espn_id":aid,"stats":{}})
                for label,raw in zip(labels,entry.get("stats") or []):
                    target=mapper.get(str(label).upper())
                    if not target:continue
                    if target=="PASS_CMP_ATT":
                        parts=str(raw).split("/")
                        if len(parts)==2:
                            c,a=num(parts[0]),num(parts[1])
                            if c is not None:record["stats"]["PASS_CMP"]=c
                            if a is not None:record["stats"]["PASS_ATT"]=a
                    else:
                        value=num(raw)
                        if value is not None:record["stats"][target]=value
    for record in players.values():
        stats=record["stats"]
        if "RUSH_YDS" in stats and "REC_YDS" in stats:stats["RUSH_REC_YDS"]=stats["RUSH_YDS"]+stats["REC_YDS"]
        if "PASS_YDS" in stats and "RUSH_YDS" in stats:stats["PASS_RUSH_YDS"]=stats["PASS_YDS"]+stats["RUSH_YDS"]
        if "RUSH_TD" in stats and "REC_TD" in stats:stats["ANY_TD"]=stats["RUSH_TD"]+stats["REC_TD"]
    return list(players.values())

def parse_scoreboard(board,schedule):
    result={}
    games={tuple(sorted((str(g["away"]).upper(),str(g["home"]).upper()))):g for g in schedule}
    for event in board.get("events",[]):
        contest=(event.get("competitions") or [{}])[0]
        sides=contest.get("competitors") or []
        teams={}
        for x in sides:
            t=(x.get("team") or {}).get("abbreviation","").upper()
            if t:teams[x.get("homeAway")]=t
        away,home=teams.get("away"),teams.get("home")
        if not away or not home:continue
        game=games.get(tuple(sorted((away,home))))
        if not game:continue
        event_date=event.get("date") or ""
        # Never allow a same-team rematch outside the scheduled kickoff.
        try:
            scheduled=datetime.fromisoformat(game["kickoff_utc"].replace("Z","+00:00"))
            actual=datetime.fromisoformat(event_date.replace("Z","+00:00"))
            if abs((actual-scheduled).total_seconds())>2*86400:continue
        except (ValueError,TypeError,KeyError):continue
        status=((event.get("status") or {}).get("type") or {})
        state=status.get("state","pre")
        score=lambda side: next((num(x.get("score")) for x in sides if x.get("homeAway")==side),None)
        clock=(event.get("status") or {}).get("displayClock")
        period=(event.get("status") or {}).get("period")
        result[game["game_id"]]={
            "game_id":game["game_id"],"espn_event_id":str(event.get("id","")),
            "status":state if state in ("pre","in","post") else "unknown",
            "status_text":status.get("shortDetail") or status.get("description") or "Unverified",
            "period":period,"clock":clock,"away":away,"home":home,
            "away_score":score("away"),"home_score":score("home"),"players":[]
        }
    return result

def snapshot(now=None,fetch=load,data_dir=DATA):
    now=now or datetime.now(timezone.utc)
    manifest=json.loads((data_dir/"schedule_2026.json").read_text())
    games=[g for g in manifest["games"] if
           now-timedelta(hours=20)<=datetime.fromisoformat(g["kickoff_utc"].replace("Z","+00:00"))<=now+timedelta(hours=4)]
    if not games:return {"season":2026,"checked_at":now.isoformat(),"source":"espn_public_scoreboard",
                         "games":[],"status":"no_active_window"}
    # Query source gameday and current UTC day to cover ET evening games.
    dates={datetime.fromisoformat(g["kickoff_utc"].replace("Z","+00:00")).strftime("%Y%m%d") for g in games}
    dates.add(now.strftime("%Y%m%d"))
    found={}
    errors=[]
    for date in sorted(dates):
        try:
            returned=parse_scoreboard(fetch(SCOREBOARD.format(date=date)),games)
            found.update(returned)
        except Exception as exc:
            errors.append(f"scoreboard {date}: {type(exc).__name__}")
    for game in found.values():
        if game["status"] not in ("in","post") or not game["espn_event_id"]:continue
        try:
            data=fetch(SUMMARY.format(event=game["espn_event_id"]))
            game["players"]=parse_summary(data,game["away"],game["home"])
            game["player_stats_status"]="available" if game["players"] else "not_published"
        except Exception as exc:
            game["player_stats_status"]="source_unavailable"
            errors.append("summary "+game["game_id"]+": "+type(exc).__name__)
    return {"season":2026,"checked_at":now.isoformat(),"source":"espn_public_scoreboard",
            "status":"ok" if found and not errors else "partial_or_unavailable",
            "errors":errors,"games":list(found.values())}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output",type=Path,default=DATA/"live_2026.json")
    args=a.parse_args()
    result=snapshot()
    if result["status"]=="partial_or_unavailable" and not result["games"]:
        raise SystemExit("ESPN NFL live provider unavailable; refusing empty overwrite")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.output.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result,indent=2)+"\n")
    os.replace(tmp,args.output)
    print("NFL LIVE SNAPSHOT:",result["status"],len(result["games"]),
          "games",sum(len(g["players"]) for g in result["games"]),"player records")
if __name__=="__main__":main()

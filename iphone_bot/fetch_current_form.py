"""Collect completed 2026-27 regular-season NBA box scores from ESPN's public
scoreboard and summary endpoints, without a paid key.

This feed is independent of the archival training dataset. It produces
descriptive recent-game stats, NOT trained-model probabilities.
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import statistics
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/current_form.json"
BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
START=dt.date(2026,10,20)
HEADERS={"User-Agent":"Sports-Bot-Research/1.0","Accept":"application/json"}
STATS={"MIN":"minutes","PTS":"PTS","REB":"REB","AST":"AST","3PT":"FG3","TO":"TOV"}
def read(endpoint,params):
    url=BASE+endpoint+"?"+urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers=HEADERS)
            with urllib.request.urlopen(req,timeout=22) as response:
                return json.load(response)
        except Exception as e:
            if attempt==2:raise RuntimeError(f"{endpoint} request failed: {type(e).__name__}") from e
            time.sleep(1+attempt)
def asnum(x):
    try:
        value=float(str(x).split(":")[0])
        return value if value>=0 else None
    except (TypeError,ValueError):
        return None
def parse_game(event):
    event_id=str(event["id"])
    payload=read("summary",{"event":event_id})
    result=[]
    teams={str(c["team"].get("id")):c["team"] for c in event.get("competitions",[{}])[0].get("competitors",[])}
    # Require final result from the source scoreboard.
    for side in payload.get("boxscore",{}).get("players",[]):
        t=side.get("team",{})
        teamid=str(t.get("id",""))
        abbr=str(t.get("abbreviation","")).upper()
        if not teamid or teamid not in teams:continue
        for group in side.get("statistics",[]):
            labels=group.get("labels",[])
            if not labels:continue
            for entry in group.get("athletes",[]):
                athlete=entry.get("athlete",{})
                values=entry.get("stats",[])
                if entry.get("didNotPlay") or len(values)!=len(labels):continue
                stats=dict(zip(labels,values))
                if not all(s in stats for s in ("MIN","PTS","REB","AST")):continue
                mins=asnum(stats["MIN"])
                pts=asnum(stats["PTS"])
                reb=asnum(stats["REB"])
                ast=asnum(stats["AST"])
                if mins is None or mins<1 or any(v is None for v in (pts,reb,ast)):continue
                name=str(athlete.get("displayName","")).strip()
                pid=str(athlete.get("id","")).strip()
                if not name or not pid:continue
                result.append({"id":pid,"player":name,"team":abbr,"team_id":teamid,
                    "event_id":event_id,"game_date":dt.datetime.fromisoformat(str(event.get("date","")).replace("Z","+00:00")).astimezone(ZoneInfo("America/New_York")).date().isoformat(),
                    "PTS":pts,"REB":reb,"AST":ast,"PRA":pts+reb+ast,"MIN":mins})
    if len(result)<8:raise ValueError(f"Incomplete player box score for event {event_id}: {len(result)} rows")
    return result
def main():
    end=dt.datetime.now(dt.timezone.utc).date()
    if end<START:raise SystemExit("2026-27 regular season hasn't begun")
    # Daily windows avoid silently truncated large range results.
    events={}
    for i in range(0,(end-START).days+1,7):
        a=START+dt.timedelta(days=i)
        b=min(end,a+dt.timedelta(days=6))
        scoreboard=read("scoreboard",{"dates":a.strftime("%Y%m%d")+"-"+b.strftime("%Y%m%d"),
                                      "seasontype":2,"limit":150})
        for event in scoreboard.get("events",[]):
            comps=event.get("competitions",[])
            if not comps:continue
            status=event.get("status",{}).get("type",{})
            if status.get("completed") is not True:continue
            if len(comps[0].get("competitors",[]))!=2:continue
            events[str(event["id"])]=event
    if not events:raise ValueError("No completed 2026-27 NBA games found")
    print("Found",len(events),"completed regular-season NBA games",flush=True)
    all_rows=[];fail=[]
    with cf.ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(parse_game,e):gid for gid,e in events.items()}
        for future in cf.as_completed(futures):
            try:all_rows.extend(future.result())
            except Exception as e:
                fail.append(futures[future])
    if len(all_rows)<100 or len(fail)>max(4,len(events)//6):
        raise ValueError(f"Data coverage insufficient: {len(all_rows)} player rows, {len(fail)} game failures")
    # Count unique completed games per player; do not mix players of same name.
    grouped={}
    for r in all_rows:
        grouped.setdefault(r["id"],{})[r["event_id"]]=r
    players=[]
    for playerid,games in grouped.items():
        rows=sorted(games.values(),key=lambda r:(r["game_date"],r["event_id"]))
        if len(rows)<3:continue
        newest=rows[-1]
        item={"player":newest["player"],"player_id":playerid,
            "team":newest["team"],"latest_game":newest["game_date"],
            "games":len(rows),"metrics":{}}
        for market in ("PTS","REB","AST","PRA","MIN"):
            vals=[r[market] for r in rows]
            item["metrics"][market]={"l3":round(statistics.mean(vals[-3:]),2),
                "l5":round(statistics.mean(vals[-5:]),2) if len(vals)>=5 else None,
                "l10":round(statistics.mean(vals[-10:]),2) if len(vals)>=10 else None,
                "season":round(statistics.mean(vals),2)}
        players.append(item)
    players.sort(key=lambda x:x["player"])
    if len(players)<80:raise ValueError(f"Too few current-season players: {len(players)}")
    output={"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "season":"2026-27","completed_games":len(events),
        "box_score_games":len(events)-len(fail),"failed_game_count":len(fail),
        "player_count":len(players),"source":"ESPN public completed-game box scores",
        "is_ai":False,"is_prizepicks":False,
        "disclaimer":"2026-27 observed form: last 3/5/10 games and season averages. Not AI-generated probabilities or an injury-adjusted projection. Verify player/team/game before using against market odds.",
        "players":players}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(output,indent=2)+"\n")
    print("Published",len(players),"player current-form summaries from",len(events)-len(fail),"box scores",flush=True)
if __name__=="__main__": main()

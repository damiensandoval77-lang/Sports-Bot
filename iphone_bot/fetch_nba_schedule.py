"""Independent NBA game schedule for Eastern calendar dates (no betting lines).

ESPN public scoreboard is THIRD-PARTY schedule context, not official NBA
availability, a sportsbook quote, or proof a player is active.
"""
import datetime as dt
import json
import pathlib
import urllib.parse
import urllib.request
import urllib.error
import time
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/nba_schedule.json"
ENDPOINT="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
NBA_CDN_SCHEDULES=(
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
)
STATUS=ROOT/"docs/nba_schedule_status.json"
EASTERN=ZoneInfo("America/New_York")


def request_json(url):
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (compatible; Sports-Bot/1.0)",
        "Accept":"application/json",
        "Origin":"https://www.nba.com",
        "Referer":"https://www.nba.com/"})
    with urllib.request.urlopen(req,timeout=25) as response:
        return json.load(response)


def nba_name(team):
    name=str(team.get("teamName","")).strip()
    city=str(team.get("teamCity","")).strip()
    if not name:raise ValueError("No NBA team name")
    if name.lower() in ("trail blazers","76ers","clippers","lakers"):
        return (city+" "+name).strip()
    return (city+" "+name).strip()


def parse_nba_game(game,requested_dates):
    try:
        stamp=game.get("gameDateTimeUTC") or game.get("gameTimeUTC")
        if not stamp:raise ValueError("Missing NBA game UTC time")
        start=dt.datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
        if start.tzinfo is None:raise ValueError("Time missing UTC offset")
        eastern_day=start.astimezone(EASTERN).date()
        if eastern_day not in requested_dates:return None
        home=game["homeTeam"];away=game["awayTeam"]
        state={1:"pre",2:"in",3:"post"}.get(int(game.get("gameStatus",1)),"unknown")
        home_name=nba_name(home)
        away_name=nba_name(away)
        return {"id":str(game["gameId"]),"game":away_name+" @ "+home_name,
                "away":away_name,"home":home_name,
                "away_abbreviation":away.get("teamTricode"),
                "home_abbreviation":home.get("teamTricode"),
                "start":start.isoformat(),"date_eastern":eastern_day.isoformat(),
                "game_state":state}
    except (KeyError,ValueError,TypeError):
        return None


def nba_season_schedule(days,requester=request_json):
    errors=[]
    for url in NBA_CDN_SCHEDULES:
        try:
            data=requester(url)
            schedule=data["leagueSchedule"]
            blocks=schedule["gameDates"]
            if not isinstance(blocks,list) or len(blocks)<30:
                raise ValueError("NBA season schedule incomplete")
            events=[];seen=set();rejected=0
            for block in blocks:
                for game in block.get("games",[]):
                    event=parse_nba_game(game,set(days))
                    if event is None:
                        rejected+=1;continue
                    if event["id"] not in seen:
                        seen.add(event["id"]);events.append(event)
            # A full season feed can correctly contain zero games on an
            # offseason date. Current NBA season must match requested dates.
            year=int(str(schedule.get("seasonYear","0"))[:4])
            if year and not all(d.year in (year,year+1) for d in days):
                raise ValueError("NBA CDN schedule season does not match dates")
            return {"events":sorted(events,key=lambda x:x["start"]),
                    "source":"NBA public CDN season schedule","rejected":rejected}
        except (urllib.error.URLError,TimeoutError,ValueError,KeyError,TypeError) as exc:
            errors.append(type(exc).__name__+":"+str(getattr(exc,"code",""))[:8])
    raise RuntimeError("NBA schedule unavailable: "+", ".join(errors))


def read_schedule(day):
    params=urllib.parse.urlencode({"dates":day.strftime("%Y%m%d"),"limit":100})
    req=urllib.request.Request(ENDPOINT+"?"+params,
                               headers={"User-Agent":"Sports-Bot-Schedule-Research/1.0"})
    with urllib.request.urlopen(req,timeout=25) as response:
        data=json.load(response)
    if not isinstance(data,dict) or not isinstance(data.get("events"),list):
        raise ValueError("Malformed ESPN scoreboard response")
    return data["events"]


def parse_event(item,day):
    try:
        comp=item["competitions"][0]
        teams={x["homeAway"]:x["team"] for x in comp["competitors"]}
        home=teams["home"]
        away=teams["away"]
        start=dt.datetime.fromisoformat(item["date"].replace("Z","+00:00"))
        if start.tzinfo is None:raise ValueError("missing timezone")
        # ESPN date API may include games in another UTC calendar date.
        if start.astimezone(EASTERN).date()!=day:return None
        state=item.get("status",{}).get("type",{}).get("state","unknown")
        if state not in ("pre","in","post"):state="unknown"
        return {"id":str(item["id"]),"game":away["displayName"]+" @ "+home["displayName"],
                "away":away["displayName"],"home":home["displayName"],
                "away_abbreviation":away.get("abbreviation"),
                "home_abbreviation":home.get("abbreviation"),
                "start":start.isoformat(),"date_eastern":day.isoformat(),
                "game_state":state}
    except (IndexError,KeyError,TypeError,ValueError):
        return None


def collect(days,reader=read_schedule):
    events=[]
    rejected=0
    seen=set()
    for day in days:
        for item in reader(day):
            event=parse_event(item,day)
            if event is None:
                rejected+=1
                continue
            if event["id"] not in seen:
                seen.add(event["id"])
                events.append(event)
    return {"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
            "status":"THIRD_PARTY_NBA_SCHEDULE_ONLY",
            "source":"ESPN public NBA scoreboard",
            "timezone":"America/New_York",
            "dates_eastern":[x.isoformat() for x in days],
            "total_games":len(events),
            "games":sorted(events,key=lambda x:x["start"]),
            "source_records_rejected":rejected,
            "has_sportsbook_props":False,
            "has_verified_player_availability":False,
            "limitation":"Independent schedule including started/completed games. Prop board requires separately verified pregame markets; players without published lines are not invented."}


def main():
    today=dt.datetime.now(EASTERN).date()
    days=[today,today+dt.timedelta(days=1)]
    errors=[]
    try:
        nba=nba_season_schedule(days)
        report=collect(days,lambda day: [])  # Shared report shape
        report.update(games=nba["events"],total_games=len(nba["events"]),
                      source=nba["source"],source_records_rejected=nba["rejected"])
    except (RuntimeError,ValueError) as exc:
        errors.append(str(exc))
        try:
            report=collect(days)
        except (urllib.error.URLError,TimeoutError,ValueError,KeyError) as espn_error:
            errors.append("ESPN:"+type(espn_error).__name__+
                          "("+str(getattr(espn_error,"code","unknown"))+")")
            STATUS.write_text(json.dumps({
                "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                "status":"ALL_SCHEDULE_SOURCES_FAILED",
                "source_failures":errors,
                "last_known_schedule_may_be_stale":True},indent=2)+"\n")
            raise RuntimeError("All NBA schedule sources failed; prior schedule remains unchanged: "+
                               "; ".join(errors)) from espn_error
    report["source_failures"]=errors
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    STATUS.write_text(json.dumps({
        "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":"SCHEDULE_FETCHED","source":report["source"],
        "total_games":report["total_games"],"source_failures":errors,
        "last_known_schedule_may_be_stale":False},indent=2)+"\n")
    print("NBA SCHEDULE:",len(report["games"]),"games for",report["dates_eastern"],
          "source:",report["source"],flush=True)


if __name__=="__main__":main()

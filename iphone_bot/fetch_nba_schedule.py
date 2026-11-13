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
SEASON_ARCHIVE=ROOT/"docs/nba_season_schedule_2026_27.json"
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


def safe_score(value):
    """A published non-negative integer basketball score, never a guess."""
    try:
        if value is None or isinstance(value,bool):return None
        n=int(value)
        if str(value).strip() not in (str(n),str(n)+".0"):return None
        return n if 0<=n<=250 else None
    except (TypeError,ValueError):return None


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
                "away_score":safe_score(away.get("score")) if state in ("in","post") else None,
                "home_score":safe_score(home.get("score")) if state in ("in","post") else None,
                "period":game.get("period") if state=="in" else None,
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
        competitors={x["homeAway"]:x for x in comp["competitors"]}
        status=item.get("status",{})
        status_type=status.get("type",{})
        return {"id":str(item["id"]),"game":away["displayName"]+" @ "+home["displayName"],
                "away":away["displayName"],"home":home["displayName"],
                "away_abbreviation":away.get("abbreviation"),
                "home_abbreviation":home.get("abbreviation"),
                "away_score":safe_score(competitors["away"].get("score")) if state in ("in","post") else None,
                "home_score":safe_score(competitors["home"].get("score")) if state in ("in","post") else None,
                "period":status.get("period") if state=="in" else None,
                "clock":status.get("displayClock") if state=="in" else None,
                "status_detail":status_type.get("shortDetail") if state in ("in","post") else None,
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


def odds_schedule_fallback(days, odds_path=ROOT/"docs/data.json"):
    """Previously fetched sportsbook fixtures only; PARTIAL and may be stale."""
    if not odds_path.exists():
        raise ValueError("No cached sportsbook event file")
    data=json.loads(odds_path.read_text())
    rows=data.get("events_covered") or data.get("picks") or []
    allowed=set(days);events={};rejected=0
    for row in rows:
        start_raw=row.get("start")
        label=row.get("game")
        try:
            start=dt.datetime.fromisoformat(str(start_raw).replace("Z","+00:00"))
            if start.tzinfo is None:raise ValueError("No timezone")
            day=start.astimezone(EASTERN).date()
            if day not in allowed:continue
            parts=str(label).split(" @ ")
            if len(parts)!=2 or not all(parts):raise ValueError("Bad matchup")
            away,home=parts
            eid=str(row.get("id") or (label+"|"+start.isoformat()))
            events.setdefault((label,start.isoformat()),{
                "id":eid,"game":label,"away":away,"home":home,
                "away_abbreviation":None,"home_abbreviation":None,
                "start":start.isoformat(),"date_eastern":day.isoformat(),
                "game_state":"unknown"})
        except (ValueError,TypeError,KeyError):
            rejected+=1
    if not events:
        raise ValueError("Cached odds contained no qualifying fixtures")
    return {"events":sorted(events.values(),key=lambda x:x["start"]),
            "source":"Cached sportsbook fixtures (partial; NOT complete NBA schedule)",
            "rejected":rejected}


def main():
    import os
    today=dt.datetime.now(EASTERN).date()
    days=[today,today+dt.timedelta(days=1)]
    errors=[]
    source_mode=os.environ.get("NBA_SCHEDULE_SOURCE_MODE","auto")
    # Preserve a newer verified-score provider snapshot instead of replacing
    # it with old sportsbook fixtures from the repository checkout.
    if source_mode=="cached" and OUTPUT.exists():
        try:
            previous=json.loads(OUTPUT.read_text())
            if previous.get("status")=="PROVIDER_NBA_SCORES_PARTIAL_SLATE":
                # Cached sportsbook fixture data cannot supersede a scored
                # feed, even when the latter is older than twelve hours.
                # Only the independently validated score workflow may replace it.
                print("Preserving provider-score slate; never replacing it with unscored cached odds",flush=True)
                return
        except (ValueError,TypeError):
            pass
    report=collect(days,lambda _: [])
    schedule=None
    if source_mode=="auto":
        try:
            schedule=nba_season_schedule(days)
        except (RuntimeError,ValueError) as exc:
            errors.append(str(exc))
            try:
                report=collect(days)
                schedule={"events":report["games"],"source":report["source"],
                          "rejected":report["source_records_rejected"]}
            except (urllib.error.URLError,TimeoutError,ValueError,KeyError) as exc2:
                errors.append("ESPN:"+type(exc2).__name__+
                              "("+str(getattr(exc2,"code","unknown"))+")")
    if schedule is None:
        try:
            schedule=odds_schedule_fallback(days)
        except (ValueError,OSError,TypeError) as exc:
            errors.append("Odds cache:"+str(exc))
    # A verified published season calendar is the persistent safety net.
    # ESPN's daily feed can omit games or go offline; never replace genuine
    # fixed future fixtures with a short/empty sportsbook fallback.
    if SEASON_ARCHIVE.exists():
        try:
            try:
                from .season_schedule_baseline import reconcile_window
            except ImportError:
                from season_schedule_baseline import reconcile_window
            archive=json.loads(SEASON_ARCHIVE.read_text())
            trusted_daily=(schedule or {}).get("events",[]) if schedule and (
                "Cached sportsbook" not in schedule.get("source","")) else []
            restored=reconcile_window(archive,days,trusted_daily)
            schedule={
                "events":restored["games"],
                "source":("NBA published full-season baseline + "
                          + str(schedule.get("source","daily source unavailable"))
                          if trusted_daily else "Cached verified NBA published full-season baseline"),
                "rejected":(schedule or {}).get("rejected",0),
                "baseline_total":restored["season_baseline_total"],
                "baseline_recovered":restored["baseline_recovered"],
            }
        except (OSError,ValueError,TypeError,KeyError) as exc:
            errors.append("NBA full-season cache:"+type(exc).__name__)
    if schedule is None:
        report["status"]="SCHEDULE_UNAVAILABLE"
        report["source"]="No validated schedule source"
        report["coverage_complete"]=False
    else:
        report.update(games=schedule["events"],total_games=len(schedule["events"]),
                      source=schedule["source"],
                      source_records_rejected=schedule["rejected"])
        report["coverage_complete"]=("Cached sportsbook" not in schedule["source"])
        if schedule.get("baseline_total"):
            report["season_baseline_status"]="VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE"
            report["season_baseline_total"]=schedule["baseline_total"]
            report["baseline_recovered"]=schedule["baseline_recovered"]
        if not report["coverage_complete"]:
            report["status"]="PARTIAL_CACHED_SPORTSBOOK_SCHEDULE"
    report["source_failures"]=errors
    report["source_mode"]=source_mode
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    STATUS.write_text(json.dumps({
        "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":("SCHEDULE_FETCHED" if report["coverage_complete"] else
                  "PARTIAL_SCHEDULE" if report["total_games"] else "SCHEDULE_UNAVAILABLE"),
        "source":report["source"],"total_games":report["total_games"],
        "source_failures":errors,
        "coverage_complete":report["coverage_complete"]},indent=2)+"\n")
    print("NBA SCHEDULE:",report["total_games"],"source:",report["source"],
          "coverage_complete:",report["coverage_complete"],flush=True)


if __name__=="__main__":main()

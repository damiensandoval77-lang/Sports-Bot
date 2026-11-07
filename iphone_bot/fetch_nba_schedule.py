"""Independent NBA game schedule for Eastern calendar dates (no betting lines).

ESPN public scoreboard is THIRD-PARTY schedule context, not official NBA
availability, a sportsbook quote, or proof a player is active.
"""
import datetime as dt
import json
import pathlib
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/nba_schedule.json"
ENDPOINT="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
EASTERN=ZoneInfo("America/New_York")


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
    report=collect([today,today+dt.timedelta(days=1)])
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print("NBA SCHEDULE:",len(report["games"]),"games for",report["dates_eastern"],flush=True)


if __name__=="__main__":main()

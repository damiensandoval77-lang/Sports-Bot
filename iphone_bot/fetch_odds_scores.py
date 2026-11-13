"""Publish NBA slate and verified live/final scores from The Odds API.

A server-side GitHub Actions job uses ODDS_API_KEY; no key is exposed in docs.
The provider /scores endpoint is distinct from sportsbook player prop prices.
It may omit NBA games: coverage_complete is ALWAYS False.
"""
import datetime as dt
import json
import math
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/nba_schedule.json"
STATUS=ROOT/"docs/nba_schedule_status.json"
BASE="https://api.the-odds-api.com/v4/sports/basketball_nba/scores/"
EASTERN=ZoneInfo("America/New_York")


def numeric_score(value):
    if value is None or isinstance(value,bool):return None
    try:
        parsed=float(value)
    except (TypeError,ValueError):return None
    return int(parsed) if math.isfinite(parsed) and parsed.is_integer() and 0<=parsed<=250 else None


def parse_game(item):
    """Only publish scores attached to the correct team name and game."""
    try:
        away=str(item["away_team"]).strip()
        home=str(item["home_team"]).strip()
        start=dt.datetime.fromisoformat(str(item["commence_time"]).replace("Z","+00:00"))
        if not away or not home or away==home or start.tzinfo is None:
            raise ValueError("Invalid identity")
        scores=item.get("scores")
        by_team={}
        if isinstance(scores,list):
            for row in scores:
                name=str(row.get("name","")).strip()
                value=numeric_score(row.get("score"))
                if name in (away,home) and value is not None:
                    by_team[name]=value
        has_pair=away in by_team and home in by_team
        completed=item.get("completed") is True
        # If scores are absent the game has no verified live state.
        state="post" if completed else ("in" if has_pair else
                "pre" if start>dt.datetime.now(dt.timezone.utc) else "unknown")
        # A completed marker with no score is not fabricated.
        update=item.get("last_update")
        parsed_update=None
        if update:
            try:
                parsed_update=dt.datetime.fromisoformat(str(update).replace("Z","+00:00"))
                if parsed_update.tzinfo is None:parsed_update=None
            except ValueError:pass
        return {"id":str(item["id"]),
                "game":away+" @ "+home,
                "away":away,"home":home,
                "away_abbreviation":None,"home_abbreviation":None,
                "away_score":by_team[away] if has_pair else None,
                "home_score":by_team[home] if has_pair else None,
                "start":start.isoformat(),
                "date_eastern":start.astimezone(EASTERN).date().isoformat(),
                "game_state":state,"score_updated_at":parsed_update.isoformat() if parsed_update else None,
                "period":None,"clock":None,"status_detail":None}
    except (KeyError,TypeError,ValueError,AttributeError):
        return None


def build_feed(items,now=None):
    if now is None:now=dt.datetime.now(dt.timezone.utc)
    if not isinstance(items,list):raise ValueError("Odds scores endpoint did not return an array")
    day=now.astimezone(EASTERN).date()
    days={day-dt.timedelta(days=1),day,day+dt.timedelta(days=1)}
    games={}
    rejected=0
    for item in items:
        parsed=parse_game(item)
        if not parsed:
            rejected+=1;continue
        if dt.date.fromisoformat(parsed["date_eastern"]) not in days:continue
        identity=(parsed["game"],parsed["start"])
        if identity in games:
            # Conflicting duplicate fixtures are a provider data error.
            if games[identity]!=parsed:raise ValueError("Conflicting duplicate NBA game")
            continue
        games[identity]=parsed
    sorted_games=sorted(games.values(),key=lambda x:x["start"])
    return {"generated_at":now.isoformat(),
            "status":"PROVIDER_NBA_SCORES_PARTIAL_SLATE",
            "source":"The Odds API NBA scores",
            "timezone":"America/New_York",
            "dates_eastern":sorted(x.isoformat() for x in days),
            "total_games":len(sorted_games),
            "games":sorted_games,
            "source_records_rejected":rejected,
            "coverage_complete":False,
            "has_sportsbook_props":False,
            "has_verified_player_availability":False,
            "limitations":["Scores originate from The Odds API; no quarter or game clock is provided.",
                           "The provider may omit some scheduled NBA games.",
                           "A missing score does not imply 0 points or a game cancellation.",
                           "Historical sportsbook snapshots do not constitute live scores."]}


def request_scores(key):
    # Including last-day finals costs two provider credits per request.
    query=urllib.parse.urlencode({"apiKey":key,"daysFrom":1,"dateFormat":"iso"})
    req=urllib.request.Request(BASE+"?"+query,headers={"User-Agent":"Sports-Bot/2.0"})
    with urllib.request.urlopen(req,timeout=22) as response:
        return json.load(response),response.headers.get("x-requests-remaining")


def write_status(status,**details):
    STATUS.write_text(json.dumps({
        "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":status,"source":"The Odds API NBA scores",
        **details},indent=2)+"\n")


def main():
    if os.environ.get("SPORTS_BOT_ENABLE_PAID_ODDS") != "1":
        write_status("PAID_ODDS_POLLING_DISABLED", coverage_complete=False,
                     note="No paid score call; existing ESPN/NBA schedule preserved.")
        print("Paid score polling disabled; preserving existing schedule.",flush=True)
        return
    key=os.environ.get("ODDS_API_KEY","").strip()
    if not key:
        write_status("MISSING_ODDS_API_KEY",coverage_complete=False)
        print("NBA score refresh skipped: ODDS_API_KEY not configured",flush=True)
        return
    try:
        items,remaining=request_scores(key)
        report=build_feed(items)
        if not report["games"]:
            write_status("NO_PROVIDER_GAMES",coverage_complete=False,
                         note="Preserved last published games; provider returned no matching NBA fixtures")
            print("NBA score API returned no matching games; retaining published schedule",flush=True)
            return
        OUT.write_text(json.dumps(report,indent=2)+"\n")
        write_status("SCORES_FETCHED",coverage_complete=False,
                     games=report["total_games"],remaining_provider_credits=remaining)
        print("NBA games from score endpoint:",report["total_games"],
              "with paired scores:",sum(x["away_score"] is not None for x in report["games"]),
              "credits remaining:",remaining,flush=True)
    except (urllib.error.URLError,TimeoutError,ValueError,KeyError,TypeError) as exc:
        code=exc.code if isinstance(exc,urllib.error.HTTPError) else None
        write_status("SCORE_PROVIDER_FAILED",coverage_complete=False,
                     http_status=code,error_type=type(exc).__name__)
        raise SystemExit("NBA scores provider failed; existing schedule preserved")


if __name__=="__main__":main()

"""Reconcile incomplete third-party fixtures with individually verified NBA.com games.

Official game evidence is dated, includes NBA game ID, official URL and fixed
Eastern kickoff. This is NOT a general-purpose sports fixture generator.
Never overwrite real scores or claim missing games have markets.
"""
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/"docs/verified_official_nba_fixtures.json"
OUT=ROOT/"docs/nba_schedule.json"
STATUS=ROOT/"docs/nba_schedule_status.json"
ET=ZoneInfo("America/New_York")
TEAMS={"ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET","GSW",
       "HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN","NOP","NYK",
       "OKC","ORL","PHI","PHX","POR","SAC","SAS","TOR","UTA","WAS"}

def matchup_id(game):
    return (game.get("date_eastern"),game.get("away_abbreviation"),game.get("home_abbreviation"))

def reconcile(schedule,evidence):
    if evidence.get("status")!="NBA_OFFICIAL_GAME_DETAILS_MANUALLY_VERIFIED":
        raise ValueError("NBA fixture evidence not verified")
    raw=schedule.get("games")
    if not isinstance(raw,list):
        raise ValueError("Schedule missing games")
    known={}
    for g in raw:
        if not isinstance(g,dict):raise ValueError("Malformed scheduled event")
        k=matchup_id(g)
        if not all(k) or k in known:raise ValueError("Duplicate or invalid games")
        known[k]=dict(g)
    additions=[]
    active_dates=set(schedule.get("dates_eastern") or [])
    for src in evidence.get("fixtures",[]):
        if src.get("date_eastern") not in active_dates:
            continue
        fixture=dict(src)
        date=fixture.get("date_eastern")
        stamp=dt.datetime.fromisoformat(str(fixture.get("start")).replace("Z","+00:00"))
        if stamp.tzinfo is None or stamp.astimezone(ET).date().isoformat()!=date:
            raise ValueError("Official fixture timestamp/day mismatch")
        gid=str(fixture.get("id",""))
        url=fixture.get("official_url","")
        loc=urlparse(url)
        if (not re.fullmatch(r"00226\d{5}",gid) or
            loc.scheme!="https" or loc.hostname not in ("nba.com","www.nba.com")
            or gid not in loc.path or
            fixture.get("source")!="NBA_OFFICIAL_GAME_PAGE" or
            fixture.get("home_abbreviation") not in TEAMS or
            fixture.get("away_abbreviation") not in TEAMS or
            fixture["away_abbreviation"]==fixture["home_abbreviation"] or
            fixture.get("game")!=fixture.get("away")+" @ "+fixture.get("home")):
            raise ValueError("Untrusted manually verified NBA fixture")
        k=matchup_id(fixture)
        if k in known:
            prior=known[k]
            if abs((stamp-dt.datetime.fromisoformat(prior["start"].replace("Z","+00:00"))).total_seconds())>1800:
                raise ValueError("Conflicting NBA tip times between official and cached source")
            continue
        known[k]=fixture
        additions.append({"date_eastern":date,"game":fixture["game"],
                          "id":gid,"official_url":url})
    games=sorted(known.values(),key=lambda x:(x.get("start",""),x.get("game","")))
    expectations=evidence.get("official_expected_daily_counts",{})
    daily={}
    for day,expected in expectations.items():
        if day not in active_dates:
            continue
        actual=sum(g.get("date_eastern")==day for g in games)
        daily[day]={"observed":actual,"official_expected":expected,
                    "complete":actual==expected}
        if actual!=expected:
            raise ValueError("NBA official slate count mismatch for "+day+
                             ": expected "+str(expected)+" got "+str(actual))
    result=dict(schedule)
    result.update(games=games,total_games=len(games),
                  official_fixture_reconciliation={
                      "status":"OFFICIAL_DAY_COUNTS_VERIFIED" if daily else "NO_COUNT_REFERENCE",
                      "verified_daily_counts":daily,
                      "newly_recovered":additions,
                      "official_daily_schedule_url":evidence.get("official_daily_schedule_url"),
                  })
    result["coverage_complete"]=schedule.get("coverage_complete") is True and all(
        x["complete"] for x in daily.values())
    if additions:
        result["source"]=str(schedule.get("source",""))+" + NBA.com verified fixtures"
    return result

def main():
    schedule=json.loads(OUT.read_text())
    evidence=json.loads(FIX.read_text())
    updated=reconcile(schedule,evidence)
    OUT.write_text(json.dumps(updated,indent=2)+"\n")
    st=json.loads(STATUS.read_text()) if STATUS.exists() else {}
    st["total_games"]=updated["total_games"]
    st["coverage_complete"]=updated["coverage_complete"]
    st["official_fixture_reconciliation"]=updated["official_fixture_reconciliation"]
    STATUS.write_text(json.dumps(st,indent=2)+"\n")
    print("OFFICIAL NBA RECONCILIATION:",
          updated["total_games"],"games total",
          len(updated["official_fixture_reconciliation"]["newly_recovered"]),"recovered",
          updated["official_fixture_reconciliation"]["verified_daily_counts"])

if __name__=="__main__":
    main()

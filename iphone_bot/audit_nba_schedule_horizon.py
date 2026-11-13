"""No-credit forward NBA fixture coverage audit against the released season."""
import datetime as dt
import json
import sys
from pathlib import Path
from iphone_bot.season_schedule_baseline import validate, ET
ROOT=Path(__file__).resolve().parents[1]/"docs"
def audit(master,daily,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    issues=[]
    try:master=validate(master)
    except (ValueError,KeyError,TypeError) as exc:
        return {"status":"BLOCKED","checked_at":now.isoformat(),
                "reason_codes":["SEASON_BASELINE_MISSING_OR_INVALID"],
                "details":str(exc)[:150],"next_14_days":[]}
    today=now.astimezone(ET).date()
    days=[(today+dt.timedelta(days=i)).isoformat() for i in range(14)]
    published={d:[] for d in days}
    for g in master["games"]:
        if g["date_eastern"] in published: published[g["date_eastern"]].append(g)
    live=daily.get("games") if isinstance(daily.get("games"),list) else []
    active=set(daily.get("dates_eastern") or [])
    verified={}
    for d in days[:2]:
        expected=published[d]
        actual=[g for g in live if g.get("date_eastern")==d]
        def teamkey(g):return(g.get("away_abbreviation"),g.get("home_abbreviation"))
        missing=[]
        for g in expected:
            if not any(teamkey(x)==teamkey(g) for x in actual):
                missing.append({"game":g["game"],"start":g["start"],"id":g["id"]})
        if missing:issues.append("PUBLISHED_GAMES_MISSING_FROM_DAILY_SLATE")
        if d not in active:issues.append("DAILY_DATE_NOT_PUBLISHED")
        verified[d]={"season_fixed_games":len(expected),"daily_games":len(actual),"missing":missing}
    if daily.get("coverage_complete") is not True:
        issues.append("DAILY_COVERAGE_NOT_VERIFIED")
    if daily.get("total_games")!=len(live):
        issues.append("DAILY_COUNT_INCONSISTENT")
    if len({str(g.get("id")) for g in live})!=len(live):
        issues.append("DUPLICATE_DAILY_GAME_ID")
    return {"checked_at":now.isoformat(),"status":"READY" if not issues else "DEGRADED",
        "season":"2026-27","season_fixed_games":master["total_games"],
        "reason_codes":sorted(set(issues)),"next_two_days_reconciliation":verified,
        "next_14_days":[{"date_eastern":d,"known_games":len(published[d]),
                         "games":[{"id":g["id"],"game":g["game"],"start":g["start"]} for g in published[d]]}
                        for d in days],
        "note":"Released fixtures only; unassigned NBA Cup matchups are not invented, and published tip times can change."}
def repair_daily_window(master, daily, now=None):
    """Restore calendar dates from verified fixtures, never sportsbook/player data."""
    from iphone_bot.publish_nba_schedule_atomic import stage
    now = now or dt.datetime.now(dt.timezone.utc)
    report = audit(master, daily, now=now)
    repairable = {"DAILY_DATE_NOT_PUBLISHED", "PUBLISHED_GAMES_MISSING_FROM_DAILY_SLATE"}
    if not repairable.intersection(report.get("reason_codes", [])):
        return daily
    repaired, _ = stage(daily, master, daily, master, now=now)
    return repaired

def main():
    def load(file):
        try:return json.loads((ROOT/file).read_text())
        except(OSError,ValueError):return {}
    master=load("nba_season_schedule_2026_27.json")
    daily=load("nba_schedule.json")
    if "--repair-window" in sys.argv:
        daily=repair_daily_window(master,daily)
        (ROOT/"nba_schedule.json").write_text(json.dumps(daily,indent=2)+"\n")
    result=audit(master,daily)
    (ROOT/"nba_schedule_horizon_audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print("NBA SCHEDULE HORIZON:",result["status"],result["reason_codes"])
    if result["status"]!="READY":raise SystemExit(2)
if __name__=="__main__":main()

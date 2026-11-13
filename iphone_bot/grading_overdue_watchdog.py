"""Independent source-verified NBA grading overdue watchdog.

Never asserts a game finished solely due to elapsed time; it flags overdue
final verification and settlement for investigation. Never grades forecasts.
"""
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/grading_overdue_health.json"
ET=ZoneInfo("America/New_York")
MAX_DELAY=dt.timedelta(hours=4)

def timestamp(value):
    try:
        t=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None
    except (TypeError,ValueError,OverflowError):
        return None

def identity(row):
    return tuple(str(row.get(k) or "") for k in ("player_id","team","game","start","stat"))

def assess(schedule,archive,ledger,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    # The short rolling schedule advances at midnight and MUST NOT erase
    # unfinished prior-day games from grading monitoring. Use the retained
    # verified 1,200-game 2026-27 season baseline for the rolling 48h window.
    rolling=(schedule.get("status")=="THIRD_PARTY_NBA_SCHEDULE_ONLY"
             and schedule.get("coverage_complete") is True)
    season=(schedule.get("status")=="VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE"
            and schedule.get("season")=="2026-27"
            and schedule.get("coverage")=="PUBLISHED_FIXED_REGULAR_SEASON_GAMES_ONLY"
            and schedule.get("total_games")==1200
            and len(schedule.get("games") or [])==1200)
    if not (rolling or season):
        return {"status":"OVERDUE_MONITOR_SOURCE_ERROR","checked_at":now.isoformat(),
                "errors":["VERIFIED_ROLLING_OR_SEASON_SCHEDULE_REQUIRED"],"games":[]}
    if archive.get("status")!="IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE":
        return {"status":"OVERDUE_MONITOR_SOURCE_ERROR","checked_at":now.isoformat(),
                "errors":["PREGAME_AI_ARCHIVE_UNAVAILABLE"],"games":[]}
    finals={identity(x):x for x in ledger.get("records",[])
            if x.get("status") in {"GRADED","EXCLUDED_VERIFIED_DNP","EXCLUDED_VERIFIED_NONPARTICIPANT"}
            and x.get("source_game_id") and x.get("final_source")}
    # Persist overdue checks for every game with an archived pretip AI
    # forecast, even after it ages out of the ordinary 48h game window.
    # Otherwise a missing final quietly becomes a false green two days later.
    archived_games={}
    for p in archive.get("predictions",[]):
        if (isinstance(p,dict) and p.get("is_pregame_prediction") is True
                and p.get("line") is None and p.get("game")):
            tip=timestamp(p.get("start"))
            if tip:
                archived_games.setdefault(p["game"],set()).add(tip)
    scoped={}
    for g in schedule.get("games",[]):
        if not isinstance(g,dict) or not g.get("game") or not g.get("date_eastern"):
            continue
        start=timestamp(g.get("start"))
        if not start or start>now-MAX_DELAY:
            continue
        has_archive=any(abs((start-tip).total_seconds())<=1800
                        for tip in archived_games.get(g["game"],()))
        if (now-start).total_seconds()>2*86400 and not has_archive:
            continue
        if start.astimezone(ET).date().isoformat()!=g["date_eastern"]:
            continue
        # Teams meet repeatedly throughout the season. Names alone neither
        # identify the archived meeting nor preserve separate overdue games.
        scoped[(g["game"],start)]=g
    forecast={}
    for p in archive.get("predictions",[]):
        if (not isinstance(p,dict) or
            p.get("is_pregame_prediction") is not True or p.get("line") is not None or
            p.get("stat") not in ("PTS","REB","AST","PRA")):
            continue
        captured=timestamp(p.get("captured_at"));tip=timestamp(p.get("start"))
        if not captured or not tip or not captured<tip:
            continue
        matches=[key for key in scoped if key[0]==p.get("game")
                 and abs((tip-key[1]).total_seconds())<=1800]
        if len(matches)!=1:
            continue
        k=identity(p)
        if k in forecast and forecast[k]!=p:
            forecast[k]=None
        else:
            forecast.setdefault(k,p)
    report={"status":"NO_OVERDUE_PENDING","checked_at":now.isoformat(),
            "threshold_minutes":int(MAX_DELAY.total_seconds()/60),"games":[],"issues":[],
            "schedule_source":schedule["status"],"note":"Persistent season schedule preserves games after rolling schedule resets. Overdue age is not proof of completion; only verified final player rows settle grades."}
    for (game,start),g in sorted(scoped.items()):
        selected=[p for p in forecast.values() if p is not None and p["game"]==game
                  and abs((timestamp(p["start"])-start).total_seconds())<=1800]
        if not selected:
            report["issues"].append(game+": NO_SAVED_PREGAME_AI_FORECASTS")
        unresolved=[p for p in selected if identity(p) not in finals]
        row={"game":game,"start":g["start"],
             "eligible_saved_forecasts":len(selected),
             "settled_verified":len(selected)-len(unresolved),
             "overdue_unresolved":len(unresolved),
             "status":"OVERDUE_UNGRADED" if unresolved else "SETTLED"}
        report["games"].append(row)
        if unresolved:
            report["issues"].append(game+": "+str(len(unresolved))+" FORECASTS_OVERDUE_FINAL_VERIFICATION")
    report["totals"]={
        "scanned_game_count":len(report["games"]),
        "overdue_game_count":sum(x["overdue_unresolved"]>0 for x in report["games"]),
        "overdue_forecasts":sum(x["overdue_unresolved"] for x in report["games"]),
        "settled_forecasts":sum(x["settled_verified"] for x in report["games"])}
    if report["issues"]:
        report["status"]="OVERDUE_UNGRADED"
    return report

def main():
    try:
        data=[json.loads((ROOT/name).read_text()) for name in
            ("docs/nba_season_schedule_2026_27.json",
             "docs/ai_no_line_pregame_archive.json",
             "docs/ai_forecast_actual_ledger.json")]
        result=assess(*data)
    except (OSError,ValueError,TypeError) as exc:
        result={"status":"OVERDUE_MONITOR_SOURCE_ERROR",
                "checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                "errors":[type(exc).__name__],"games":[]}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("NBA GRADING FINAL-VERIFICATION SLA",json.dumps(result))
    return 0 if result["status"]=="NO_OVERDUE_PENDING" else 1

if __name__=="__main__":sys.exit(main())

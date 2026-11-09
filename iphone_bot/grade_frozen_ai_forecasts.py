"""Grade immutable pre-tip AI-only projections against VERIFIED final player boxes.

Separate from PrizePicks and sportsbook settlement. Measures forecast errors,
never calculates bet hit rates/ROI without a pre-tip market line. Do not re-run
models after games. Historical grades persist even if the 48-hour archive rolls.
"""
import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from iphone_bot.fetch_final_boxscores import gather
from iphone_bot.paper_pick_pipeline import TEAM_ABBREVIATIONS, expected_opponents, strict_player_name
from iphone_bot.prizepicks_research_ledger import utc
from iphone_bot.recover_prizepicks_final_games import multi_origin_request

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"docs/ai_no_line_pregame_archive.json"
LEDGER=ROOT/"docs/ai_forecast_actual_ledger.json"
STATUS=ROOT/"docs/ai_forecast_grade_status.json"
ET=ZoneInfo("America/New_York")
STATS=("PTS","REB","AST","PRA")
APPROVED_SOURCES={"NBA_CDN_FINAL","ESPN_FINAL"}

def eastern_day(stamp):
    moment=utc(stamp)
    return moment.astimezone(ET).date().isoformat() if moment else None

def key(p):
    return "|".join(str(p.get(k,"")) for k in ("player_id","team","game","start","stat"))

def eligible_predictions(predictions,now=None,days_back=3):
    now=now or dt.datetime.now(dt.timezone.utc)
    floor=now.astimezone(ET).date()-dt.timedelta(days=days_back)
    result={}
    for p in predictions:
        if p.get("is_pregame_prediction") is not True or p.get("line") is not None:
            continue
        start=utc(p.get("start"));locked=utc(p.get("captured_at"))
        if not start or not locked or locked>=start or (now-start).total_seconds()<4*3600:
            continue
        if start.astimezone(ET).date()<floor:
            continue
        stat=p.get("stat")
        if stat not in STATS or not p.get("player_id") or not p.get("player") or not p.get("team"):
            continue
        opponents=expected_opponents(p.get("game"),p.get("team"))
        if len(opponents)!=1:
            continue
        try:
            projection=float(p.get("projection"))
        except (ValueError,TypeError):
            continue
        if not math.isfinite(projection) or projection<0 or projection>250:
            continue
        ident=key(p)
        if ident in result:
            # Conflicting captures are not silently resolved by newest or most favorable value.
            if result[ident]!=p:
                result[ident]=None
        else:
            result[ident]=p
    return [p for p in result.values() if p is not None]

def final_requests(predictions):
    requests={}
    for p in predictions:
        start=utc(p["start"])
        day=start.astimezone(ET).date().isoformat()
        pair=(day,p["game"])
        requests.setdefault(pair,{"event_start":p["start"],"status":"PENDING",
                                  "game":p["game"],"team":p["team"],
                                  "player_id":str(p["player_id"])})
    return list(requests.values())

def settle_predictions(predictions,final_rows,existing=None):
    """No missing player or unverified DNP is ever a zero-stat observation."""
    retained={key(r):dict(r) for r in (existing or []) if r.get("status")=="GRADED"}
    by_name=defaultdict(list)
    for row in final_rows:
        if (row.get("final_confirmed") is not True or
            row.get("source") not in APPROVED_SOURCES or
            row.get("dnp_final_verified") is True or
            not row.get("source_game_id")):
            continue
        n=strict_player_name(row.get("player"))
        if not n:continue
        ident=(n,row.get("team"),row.get("date"),row.get("opponent"))
        by_name[ident].append(row)
    new_grades=0
    for p in predictions:
        ident=key(p)
        if ident in retained:continue
        day=eastern_day(p["start"])
        opponents=expected_opponents(p["game"],p["team"])
        if len(opponents)!=1:continue
        candidates=by_name.get((strict_player_name(p["player"]),p["team"],day,opponents[0]),[])
        # Exactly one independently verified player/game; duplicates are ambiguous.
        if len(candidates)!=1:continue
        actual_row=candidates[0]
        try:
            actual=float(actual_row[p["stat"]]); projection=float(p["projection"])
            minutes=float(actual_row["MIN"])
        except (TypeError,ValueError,KeyError):
            continue
        if not all(math.isfinite(v) for v in (actual,projection,minutes)):
            continue
        if not (0<=actual<=250 and 0<minutes<=60):
            continue
        retained[ident]={
            "status":"GRADED", "player_id":str(p["player_id"]),
            "player":p["player"],"team":p["team"],"game":p["game"],
            "start":p["start"],"stat":p["stat"],
            "captured_at":p["captured_at"],"projection":projection,
            "actual":actual,"error":round(projection-actual,5),
            "absolute_error":round(abs(projection-actual),5),
            "final_source":actual_row["source"],
            "source_game_id":str(actual_row["source_game_id"]),
            "minutes":minutes,"line":None,"betting_grade":None
        }
        new_grades+=1
    return {"records":sorted(retained.values(),key=lambda x:(x["start"],x["game"],x["player"],x["stat"])),
            "new_grades":new_grades}

def report(day,predictions,graded,fetch_report=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    chosen=[p for p in predictions if eastern_day(p["start"])==day]
    records=[g for g in graded["records"] if eastern_day(g["start"])==day]
    by_key={key(g):g for g in records}
    pending=[p for p in chosen if key(p) not in by_key]
    stat_metrics={}
    for stat in STATS:
        rows=[r for r in records if r["stat"]==stat]
        stat_metrics[stat]={
            "graded":len(rows),
            "mae":round(mean(r["absolute_error"] for r in rows),3) if rows else None,
            "mean_signed_error":round(mean(r["error"] for r in rows),3) if rows else None,
        }
    return {
        "status":("AI_PRETIP_FORECASTS_GRADED" if chosen and not pending else
                  "AI_PRETIP_FORECASTS_PARTIALLY_GRADED" if records else
                  "NO_VERIFIED_AI_FORECAST_ACTUALS"),
        "generated_at":now.isoformat(),"game_date_eastern":day,
        "recorded_pregame_forecasts":len(chosen),"graded":len(records),"ungraded":len(pending),
        "new_grades":graded["new_grades"],
        "by_stat":stat_metrics,
        "ungraded_by_game":dict(sorted(Counter(p["game"] for p in pending).items())),
        "final_feed":fetch_report or {},
        "is_betting_hit_rate":False,
        "note":"Forecast-vs-actual absolute error only; no market line or bet direction. Missing players/DNP are not assigned zero."
    }

def main():
    now=dt.datetime.now(dt.timezone.utc)
    raw=json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {}
    archive=raw.get("predictions") or []
    selected=eligible_predictions(archive,now)
    old=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    requested=final_requests(selected)
    if len(requested)>25:
        raise SystemExit("More than 25 final matchups; refusing incomplete grade fetch")
    if requested:
        try:
            actuals,fetch_report=gather(requested,now=now,request=multi_origin_request)
        except (OSError,ValueError,TypeError,KeyError) as e:
            actuals=[];fetch_report={"status":"FINAL_FETCH_FAILED","errors":[type(e).__name__]}
    else:
        actuals=[];fetch_report={"status":"NO_ELIGIBLE_ARCHIVED_GAMES"}
    graded=settle_predictions(selected,actuals,old)
    LEDGER.write_text(json.dumps({"version":1,"records":graded["records"]},indent=2)+"\n")
    day=(now.astimezone(ET).date()-dt.timedelta(days=1)).isoformat()
    status=report(day,selected,graded,fetch_report,now)
    STATUS.write_text(json.dumps(status,indent=2)+"\n")
    print("AI NO-LINE GRADE:",json.dumps({
        k:status[k] for k in ("game_date_eastern","status","recorded_pregame_forecasts",
                           "graded","ungraded","new_grades")},sort_keys=True))

if __name__=="__main__":
    main()

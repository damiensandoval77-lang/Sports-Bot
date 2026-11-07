"""Four-season NBA minutes and rotation-opportunity research (NOT live inference).

Consumes the existing validated archive from download_archived_nba.py, not
sportsbook lines. Forecast each player-game from SAME-TEAM/SAME-SEASON
earlier games only. Entire 2025-26 season is the predeclared held-out evaluation.
This is observational minutes research, not verified game-day injury modeling.
"""
import csv
import json
import math
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean
try:
    from .minutes_model_v2 import forecast, numeric_minutes
    from .research_context import minutes_estimate
except ImportError:
    from minutes_model_v2 import forecast, numeric_minutes
    from research_context import minutes_estimate

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"data/nba/raw/raw_game_logs.csv"
OUTPUT=ROOT/"docs/historical_minutes_validation.json"
EXPECTED_SEASONS=("2022-23","2023-24","2024-25","2025-26")
HELD_OUT_SEASON="2025-26"
MIN_REPORT_SAMPLES=100
REQUIRED=("PLAYER_ID","GAME_ID","GAME_DATE","TEAM_ABBREVIATION","MIN","SEASON_ID")


def load_archive(path=ARCHIVE):
    """Validate identity, season boundaries and conflicting duplicate records."""
    records=[]
    seen={}
    rejected=defaultdict(int)
    with open(path,newline="",encoding="utf-8-sig") as handle:
        reader=csv.DictReader(handle)
        missing=set(REQUIRED)-set(reader.fieldnames or [])
        if missing:raise ValueError("Missing archived minute columns: "+str(sorted(missing)))
        for row in reader:
            season=str(row["SEASON_ID"]).strip()
            if season not in EXPECTED_SEASONS:
                rejected["other_season"]+=1;continue
            try:
                day=date.fromisoformat(str(row["GAME_DATE"]).strip())
            except ValueError:
                rejected["invalid_date"]+=1;continue
            start_year=int(season[:4])
            if not (date(start_year,9,1)<=day<=date(start_year+1,7,31)):
                rejected["wrong_season_date"]+=1;continue
            pid=str(row["PLAYER_ID"]).strip()
            gid=str(row["GAME_ID"]).strip()
            team=str(row["TEAM_ABBREVIATION"]).strip().upper()
            if not pid.isdigit() or not gid or not (2<=len(team)<=3 and team.isalpha()):
                rejected["bad_identity"]+=1;continue
            minutes=numeric_minutes(row["MIN"])
            if minutes is None:
                rejected["missing_or_invalid_minutes"]+=1;continue
            key=(season,pid,gid)
            entry={"season":season,"id":pid,"game_id":gid,
                   "date":day.isoformat(),"team":team,"MIN":minutes}
            if key in seen:
                previous=seen[key]
                if previous!=entry:raise ValueError("Conflicting player-game identity: "+str(key))
                rejected["identical_duplicate"]+=1
                continue
            seen[key]=entry
            records.append(entry)
    if not records:raise ValueError("No valid archived minutes games")
    return records,dict(rejected)


def _summary(samples):
    n=len(samples)
    if not n:return {"observations":0,"dates":0,"players":0,"baseline_mae":None,
                     "candidate_mae":None,"candidate_minus_baseline_mae":None,
                     "candidate_better":0,"baseline_better":0,"tied":0,
                     "baseline_bias":None,"candidate_bias":None}
    old_errors=[x["baseline"]-x["actual"] for x in samples]
    new_errors=[x["candidate"]-x["actual"] for x in samples]
    old_mae=mean(abs(x) for x in old_errors)
    new_mae=mean(abs(x) for x in new_errors)
    better=sum(abs(b)<abs(a) for a,b in zip(old_errors,new_errors))
    worse=sum(abs(b)>abs(a) for a,b in zip(old_errors,new_errors))
    return {"observations":n,"dates":len({x["date"] for x in samples}),
            "players":len({x["player_id"] for x in samples}),
            "baseline_mae":round(old_mae,3),
            "candidate_mae":round(new_mae,3),
            "candidate_minus_baseline_mae":round(new_mae-old_mae,3),
            "candidate_better":better,"baseline_better":worse,"tied":n-better-worse,
            "baseline_bias":round(mean(old_errors),3),
            "candidate_bias":round(mean(new_errors),3)}


def evaluate(records, rejected=None):
    """Forward-only chronology with both candidates on exactly the same games."""
    histories=defaultdict(lambda:deque(maxlen=12))
    observations=[]
    # Explicit sorting ensures no outcomes from later days can enter a prediction.
    for g in sorted(records,key=lambda r:(r["date"],r["game_id"],r["id"])):
        key=(g["season"],g["id"],g["team"])
        history=list(histories[key])
        prior=[{"date":x["date"],"team":g["team"],"MIN":x["MIN"]}
               for x in history if x["date"]<g["date"]]
        if len(prior)>=8:
            baseline=minutes_estimate(prior,g["date"]).get("expected_minutes")
            v2=forecast(prior,g["date"],g["team"]).get("expected_minutes")
            if baseline is not None and v2 is not None:
                old=history[-8:]
                last3=mean(x["MIN"] for x in old[-3:])
                previous5=mean(x["MIN"] for x in old[-8:-3])
                # Rotation trend uses previous games only, NOT tonight's lineup.
                trend=last3-previous5
                role="RECENT_MINUTES_UP" if trend>=4 else (
                     "RECENT_MINUTES_DOWN" if trend<=-4 else "STABLE")
                observations.append({
                    "season":g["season"],"date":g["date"],
                    "player_id":g["id"],"team":g["team"],
                    "actual":g["MIN"],"baseline":baseline,
                    "candidate":v2,"rotation_trend":role})
        # Same-day doubleheaders, if ever present, cannot inform each other.
        histories[key].append(g)
    seasons={season:_summary([x for x in observations if x["season"]==season])
             for season in EXPECTED_SEASONS}
    holdout=[x for x in observations if x["season"]==HELD_OUT_SEASON]
    earlier=[x for x in observations if x["season"]!=HELD_OUT_SEASON]
    by_trend={trend:_summary([x for x in holdout if x["rotation_trend"]==trend])
              for trend in ("RECENT_MINUTES_UP","STABLE","RECENT_MINUTES_DOWN")}
    overall=_summary(holdout)
    return {
        "status":("HISTORICAL_HOLDOUT_RESEARCH_ONLY" if overall["observations"]>=MIN_REPORT_SAMPLES
                  else "INSUFFICIENT_HISTORICAL_HOLDOUT"),
        "source":"ARCHIVED_REGULAR_SEASON_PLAYER_GAME_LOGS",
        "seasons":list(EXPECTED_SEASONS),
        "holdout_season":HELD_OUT_SEASON,
        "archive_player_games":len(records),
        "quality_rejections":rejected or {},
        "earlier_seasons":_summary(earlier),
        "holdout":overall,
        "by_season":seasons,
        "holdout_by_pregame_rotation_trend":by_trend,
        "live_model_unchanged":True,
        "production_adjustment_applied":False,
        "injury_effect_claimed":False,
        "limitations":[
            "The 2025-26 season is held out by calendar season, and no outcomes are read before tipoff.",
            "Histories reset on season and team changes; trades and offseason transitions are not merged.",
            "Only players who played positive minutes are evaluated; DNP and start predictions are not covered.",
            "Rotation trend is inferred from earlier logged minutes, not confirmed future lineup availability.",
            "Historical samples may be correlated across players/games; no injury causal claim.",
            "This evaluation cannot by itself validate any betting or live model improvement."
        ]}


def main():
    games,rejected=load_archive()
    report=evaluate(games,rejected)
    report["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print("HISTORICAL MINUTES:",json.dumps({
        "status":report["status"],"archive_player_games":report["archive_player_games"],
        "earlier":report["earlier_seasons"]["observations"],
        "holdout":report["holdout"]
    }),flush=True)


if __name__=="__main__":
    main()

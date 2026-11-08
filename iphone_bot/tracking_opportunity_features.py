"""Validated historical NBA tracking opportunity feature loader.

Input MUST contain licensed/authorized actual player-game tracking observations.
No box-score approximations are mislabeled as potential assists/rebound chances.
Missing input is a normal NOT_AVAILABLE status, never fabricated observations.
All feature windows end STRICTLY BEFORE the upcoming game date.
"""
import csv
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_CSV=ROOT/"data/nba/tracking/authorized_tracking_games.csv"
TRACKING_FIELDS=("potential_assists","passes_made","touches",
                 "assist_points_created","rebound_chances",
                 "rebound_chance_pct","contested_rebounds",
                 "uncontested_rebounds","offensive_rebound_chances",
                 "defensive_rebound_chances")
SOURCE_COLUMNS=("player_id","game_date","team","source","source_reference")
MIN_GAMES=3
FEATURE_VERSION="TRACKING_OPPORTUNITY_PREGAME_ROLLING_V1"

def _number(value):
    if value is None or str(value).strip()=="":return None
    try:
        x=float(value)
        return x if math.isfinite(x) and x>=0 else None
    except (TypeError,ValueError):return None

def load_tracking(path=DEFAULT_CSV):
    path=Path(path)
    if not path.is_file():
        return {},{"status":"SOURCE_NOT_CONNECTED","rows":0,"players":0,
                   "source":None,"feature_version":FEATURE_VERSION}
    observations=defaultdict(dict)
    rejected=0
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        missing=set(SOURCE_COLUMNS)-set(reader.fieldnames or [])
        if missing:raise ValueError("Tracking CSV missing provenance/identity fields: "+str(sorted(missing)))
        if not set(TRACKING_FIELDS).intersection(reader.fieldnames or []):
            raise ValueError("Tracking CSV must include at least one observed opportunity measure")
        for record in reader:
            player=str(record.get("player_id") or "").strip()
            day=str(record.get("game_date") or "").strip()
            team=str(record.get("team") or "").strip().upper()
            source=str(record.get("source") or "").strip()
            reference=str(record.get("source_reference") or "").strip()
            try:valid_date=date.fromisoformat(day)
            except ValueError:valid_date=None
            if not player or not valid_date or valid_date>date.today() or len(team)!=3 or not source or not reference:
                rejected+=1
                continue
            values={k:_number(record.get(k)) for k in TRACKING_FIELDS}
            if not any(v is not None for v in values.values()):
                rejected+=1
                continue
            if values["rebound_chance_pct"] is not None and values["rebound_chance_pct"]>100:
                rejected+=1
                continue
            for k in TRACKING_FIELDS:
                if k!="rebound_chance_pct" and values[k] is not None and values[k]>300:
                    rejected+=1
                    break
            else:
                key=(player,team)
                obs={"date":day,"team":team,"player_id":player,
                     "source":source,"source_reference":reference,**values}
                existing=observations[key].get(day)
                if existing is not None and existing!=obs:
                    raise ValueError("Conflicting tracking observations for "+player+" "+day)
                observations[key][day]=obs
    n=sum(len(v) for v in observations.values())
    return {k:sorted(v.values(),key=lambda r:r["date"]) for k,v in observations.items()},{
        "status":"AVAILABLE_FOR_RESEARCH" if n else "NO_VALID_ROWS",
        "rows":n,"players":len(observations),"rejected":rejected,
        "source":"AUTHORIZED_EXTERNAL_PLAYER_GAME_TRACKING",
        "feature_version":FEATURE_VERSION}

def pregame_features(tracking,player_id,team,upcoming_date,min_games=MIN_GAMES):
    history=[r for r in tracking.get((str(player_id),str(team).upper()),[])
             if r["date"]<str(upcoming_date)]
    result={"status":"NOT_AVAILABLE","feature_version":FEATURE_VERSION,
            "historical_games":len(history),"features":{},
            "no_current_game_data":True,"production_applied":False}
    if not history:return result
    computed={}
    for field in TRACKING_FIELDS:
        valid=[r[field] for r in history if r.get(field) is not None]
        if len(valid)<min_games:continue
        computed[field]={"last5":round(mean(valid[-5:]),3),
                         "last10":round(mean(valid[-10:]),3) if len(valid)>=10 else None,
                         "season":round(mean(valid),3),"observations":len(valid)}
    if not computed:return result
    return {**result,"status":"RESEARCH_TRACKING_AVAILABLE","features":computed,
            "source":"AUTHORIZED_EXTERNAL_PLAYER_GAME_TRACKING",
            "latest_recorded_date":history[-1]["date"]}

"""Forensics for extreme misses on genuinely frozen NBA pregame model inputs.

No model updates, invented minutes, retrospective feature backfill or causal
conclusion. Extremely large single-game misses can reflect outlier shooting,
blowouts, injuries, bad pregame inputs or source issues.
"""
import json
import math
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

try:
    from .model_performance import independent_rows,forecast_values,finite,utc
except ImportError:
    from model_performance import independent_rows,forecast_values,finite,utc

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"docs/extreme_miss_forensics.json"
MARKETS=("PTS","REB","AST","PRA")
EXTREME={"PTS":10.,"REB":5.,"AST":4.,"PRA":15.}
MINUTES_GAP=5.

def number(value):
    if value is None or isinstance(value,bool):return None
    n=finite(value)
    return n if n is not None and math.isfinite(n) and n>=0 else None

def summary(rows):
    return {"markets":len(rows),
            "distinct_game_dates":len({x["date"] for x in rows}),
            "extreme_misses":sum(x["extreme"] for x in rows),
            "extreme_rate":round(sum(x["extreme"] for x in rows)/len(rows),4) if rows else None,
            "mean_signed_error":round(sum(x["error"] for x in rows)/len(rows),3) if rows else None,
            "mean_absolute_error":round(sum(abs(x["error"]) for x in rows)/len(rows),3) if rows else None}

def report(records):
    unique=independent_rows(records)
    grouped=defaultdict(list)
    gaps=Counter()
    cases=[]
    for r in unique:
        stat=r.get("market")
        if stat not in MARKETS:continue
        # Prefer the exact frozen Combined prediction. Legacy settled quotes
        # may omit Combined but preserve both ORIGINAL and opponent forecasts.
        # Their arithmetic midpoint can be reconstructed from those two
        # *pregame* values only, never from any actual game outcome.
        projection=number(r.get("combined_projection"))
        if projection is None:
            projection=number(forecast_values(r)["combined"])
            if projection is not None:gaps["legacy_combined_from_frozen_components"]+=1
        actual=number(r.get("actual"))
        if projection is None or actual is None:
            gaps["missing_valid_settled_projection"]+=1
            continue
        error=projection-actual
        input_audit=r.get("model_feature_audit")
        frozen=r.get("frozen_minutes_research")
        actual_min=number(r.get("actual_minutes"))
        research_min=number(frozen.get("expected_minutes")) if isinstance(frozen,dict) else None
        model_min=None
        if isinstance(input_audit,dict) and isinstance(input_audit.get("features"),dict):
            model_min=number(input_audit["features"].get("MIN_L5"))
        if actual_min is None:gaps["missing_verified_actual_minutes"]+=1
        if research_min is None:gaps["missing_frozen_pregame_expected_minutes"]+=1
        if model_min is None:gaps["missing_frozen_production_minutes_feature"]+=1
        if actual_min is not None and not (0<actual_min<=60):
            gaps["invalid_actual_minutes"]+=1
            actual_min=None
        minutes_gap=(actual_min-research_min if actual_min is not None and research_min is not None else None)
        model_minutes_gap=(actual_min-model_min if actual_min is not None and model_min is not None else None)
        threshold=EXTREME[stat]
        case={"player_id":str(r.get("player_id")),
             "player":str(r.get("player","")),
             "team":str(r.get("team","")),
             "game":str(r.get("game","")),
             "date":utc(r["event_start"]).date().isoformat(),
             "market":stat,"projection":round(projection,3),
             "actual":actual,"error":round(error,3),
             "extreme":abs(error)>=threshold,
             "actual_minutes":actual_min,
             "frozen_research_minutes":research_min,
             "frozen_production_min_l5":model_min,
             "actual_minus_frozen_research_minutes":round(minutes_gap,3) if minutes_gap is not None else None,
             "actual_minus_production_min_l5":round(model_minutes_gap,3) if model_minutes_gap is not None else None,
             "source":r.get("settlement_source")}
        grouped[stat].append(case)
        if case["extreme"]:cases.append(case)
    split={}
    for market in MARKETS:
        rows=grouped[market]
        extreme=[r for r in rows if r["extreme"]]
        known=[r for r in extreme if r["actual_minus_frozen_research_minutes"] is not None]
        low=[r for r in known if r["actual_minus_frozen_research_minutes"]<=-MINUTES_GAP]
        high=[r for r in known if r["actual_minus_frozen_research_minutes"]>=MINUTES_GAP]
        near=[r for r in known if abs(r["actual_minus_frozen_research_minutes"])<MINUTES_GAP]
        split[market]={
            "extreme_threshold":EXTREME[market],
            "all":summary(rows),
            "extreme":summary(extreme),
            "extreme_with_frozen_minutes_and_actual":len(known),
            "extreme_under_minutes_by_at_least_5":len(low),
            "extreme_over_minutes_by_at_least_5":len(high),
            "extreme_minutes_within_5":len(near),
            "extreme_unexplained_minutes_coverage":len(extreme)-len(known)}
    return {"status":"DESCRIPTIVE_EXTREME_MISS_FORENSICS_NOT_CAUSAL",
      "method":"PREGAME_LOCKED_MODEL_FEATURES_AND_VERIFIED_ACTUAL_MINUTES",
      "independent_settled_markets":sum(len(x) for x in grouped.values()),
      "by_market":split,
      "large_misses":sorted(cases,key=lambda r:(-abs(r["error"]),r["date"],r["player"]))[:40],
      "data_gaps":dict(gaps),
      "historical_pregame_feature_backfill_permitted":False,
      "causal_explanation_established":False,
      "training_or_probability_modified":False,
      "live_predictions_modified":False,
      "limitations":[
       "Minutes discrepancies and model errors are correlated signals, not established causes.",
       "MIN_L5 is a lagged input to the trained model, NOT the trained model's predicted minutes.",
       "Expected minutes research is unverified and was NOT applied to the production forecast.",
       "Old captures without frozen inputs cannot be retroactively interpreted as pregame features.",
       "Individual markets for the same player and game are correlated.",
       "Source boxscores must be independently verified; historical minutes may be missing."]}

def main():
    records=json.loads(LEDGER.read_text()).get("records",[])
    result=report(records)
    result["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print("Extreme-miss research:",
          json.dumps({"settled_markets":result["independent_settled_markets"],
              "extreme_by_market":{k:v["extreme"]["markets"] for k,v in result["by_market"].items()},
              "missing_minutes":result["data_gaps"]},sort_keys=True),flush=True)

if __name__=="__main__":main()

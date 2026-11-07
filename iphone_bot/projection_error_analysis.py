"""Descriptive NBA AI error analysis from immutable settled pregame quotes.

Research only: no causal claims, no refitting, no change to live odds,
predictions, or simulated hit percentages. Each player/date/market is scored
once using the earliest captured pregame quote. Lookahead and duplicate
sportsbook lines are excluded.
"""
import json
import math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

try:
    from .model_performance import independent_rows,forecast_values,finite,utc
except ImportError:
    from model_performance import independent_rows,forecast_values,finite,utc

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"docs/projection_error_analysis.json"
STATS=("PTS","REB","AST","PRA")
MODELS=("original","opponent_aware","combined")

def metrics(rows):
    n=len(rows)
    if not n:
        return {"markets":0,"mae":None,"mean_bias":None,
                "over_projected":0,"under_projected":0,
                "within_2":None,"within_5":None,
                "direction_eligible":0,"direction_wins":0,
                "direction_losses":0,"direction_pushes":0,"direction_hit_rate":None}
    wins=sum(x["result"]=="WIN" for x in rows)
    losses=sum(x["result"]=="LOSS" for x in rows)
    pushes=sum(x["result"]=="PUSH" for x in rows)
    eligible=wins+losses
    return {"markets":n,
       "mae":round(sum(abs(x["error"]) for x in rows)/n,3),
       "mean_bias":round(sum(x["error"] for x in rows)/n,3),
       "over_projected":sum(x["error"]>0 for x in rows),
       "under_projected":sum(x["error"]<0 for x in rows),
       "within_2":round(sum(abs(x["error"])<=2 for x in rows)/n,4),
       "within_5":round(sum(abs(x["error"])<=5 for x in rows)/n,4),
       "direction_eligible":eligible,
       "direction_wins":wins,"direction_losses":losses,
       "direction_pushes":pushes,
       "direction_hit_rate":round(wins/eligible,4) if eligible else None}

def report(records):
    records=independent_rows(records)
    rows=[]
    counts=defaultdict(int)
    for r in records:
        try:
            capture=utc(r["captured_at"]);start=utc(r["event_start"])
            if capture>=start:counts["late"]+=1;continue
            market=str(r["market"])
            if market not in STATS:continue
            actual=finite(r["actual"]);line=finite(r["line"])
            predictions=forecast_values(r)
            if actual is None or actual<0 or line is None or line<0:
                counts["invalid"]+=1;continue
            for model in MODELS:
                pred=predictions[model]
                if pred is None or pred<0:continue
                side="OVER" if pred>line else "UNDER" if pred<line else "NO_LEAN"
                result=("PUSH" if actual==line else
                        "NO_LEAN" if side=="NO_LEAN" else
                        "WIN" if (actual>line)==(side=="OVER") else "LOSS")
                rows.append({"game":r.get("game"),"game_date_utc":start.date().isoformat(),
                    "event_start":start.isoformat(),"player":r.get("player"),
                    "player_id":str(r.get("player_id")),"team":r.get("team"),
                    "market":market,"model":model,
                    "projection":round(pred,3),"actual":actual,
                    "line":line,"direction":side,"result":result,
                    "error":round(pred-actual,3),
                    "absolute_error":round(abs(pred-actual),3),
                    "source":r.get("settlement_source"),"capture":capture.isoformat()})
        except (KeyError,ValueError,TypeError):
            counts["invalid"]+=1
    combined=[x for x in rows if x["model"]=="combined"]
    by_market={m:metrics([x for x in combined if x["market"]==m]) for m in STATS}
    by_game={}
    for game in sorted({x["game"] for x in combined}):
        by_game[game]=metrics([x for x in combined if x["game"]==game])
    # PTS, REB, AST, PRA have different natural scales; display separate
    # large misses for each rather than an unfair all-market ranking.
    largest_by_market={}
    for market in STATS:
        candidates=[x for x in combined if x["market"]==market]
        largest_by_market[market]=sorted(candidates,key=lambda x:
            (-x["absolute_error"],str(x["player"]),str(x["event_start"])))[:12]
    signed={}
    for model in MODELS:
        signed[model]=metrics([x for x in rows if x["model"]==model])
    verdict={"status":"DESCRIPTIVE_NOT_CAUSAL",
        "cannot_infer_injury_or_usage_cause":True,
        "requires_independent_future_games_before_model_promotion":True,
        "sample_independent_combined_markets":len(combined),
        "combined":signed["combined"],
        "models":signed,
        "combined_by_market":by_market,
        "combined_by_game":by_game,
        "largest_combined_misses_by_market":largest_by_market,
        "data_quality":{"invalid_excluded":counts["invalid"],"late_excluded":counts["late"]},
        "notes":["Each player, event and market counted once on earliest locked sportsbook quote.",
                 "Signed error = projected minus actual; positive means overprediction.",
                 "No injury/usage/minutes causality can be inferred from boxscores alone.",
                 "Different stat markets have different scales, so MAE across markets is not normalized.",
                 "Samples from the same game are correlated; these metrics are not evidence of profitable betting.",
                 "No model probabilities, projections, or live rankings were changed."]}
    return verdict

def main():
    ledger=json.loads(LEDGER.read_text()).get("records",[])
    result=report(ledger)
    result["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print("PROJECTION ERROR ANALYSIS",json.dumps({
        "settled_markets":result["sample_independent_combined_markets"],
        "combined":result["combined"],
        "by_market":result["combined_by_market"]},sort_keys=True),flush=True)

if __name__=="__main__":main()

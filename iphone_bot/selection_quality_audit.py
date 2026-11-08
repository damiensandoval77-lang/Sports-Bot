"""Prospective NBA selection-quality/readiness audit for Combined AI.

Only pregame-locked settled player-game-markets, one earliest bookmaker quote
per market. No training or automatic bet approval. Historical one-day market
results are not validation. Break down by frozen projected edge relative to
the quoted line and by market. Do not interpret past winning buckets as
optimized thresholds.
"""
import json
import math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .model_performance import independent_rows,utc,finite,forecast_values
except ImportError:
    from model_performance import independent_rows,utc,finite,forecast_values

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"docs/selection_quality_audit.json"
MARKETS=("PTS","REB","AST","PRA")
EDGE_BINS=((0,1),(1,2),(2,4),(4,float("inf")))
MIN_TOTAL_MARKETS=250
MIN_GAME_DATES=10
MIN_MARKET_MARKETS=75
MIN_MARKET_DATES=6

def wilson_lower(wins,n,z=1.96):
    if not n:return None
    rate=wins/n
    denom=1+z*z/n
    center=(rate+z*z/(2*n))/denom
    half=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/denom
    return round(max(0,(center-half)/denom),4)

def summarize(rows,min_markets=MIN_TOTAL_MARKETS,min_dates=MIN_GAME_DATES):
    wins=sum(r["won"] for r in rows)
    n=len(rows)
    days=len({r["game_date_eastern"] for r in rows})
    lower=wilson_lower(wins,n)
    ready=n>=min_markets and days>=min_dates
    return {"independent_markets":n,"wins":wins,"losses":n-wins,
        "hit_rate":round(wins/n,4) if n else None,
        "distinct_game_dates":days,
        "wilson_lower_95":lower,
        "sample_threshold_met":ready,
        "status":"ELIGIBLE_FOR_FUTURE_HOLDOUT_REVIEW" if ready else
            "INSUFFICIENT_MULTIDAY_VALIDATION",
        "tested_positive_edge":False}

def direction_error(rows):
    """Fixed, descriptive OVER/UNDER segments for each frozen market.

    Never select a side using these same outcomes. Only future complete
    game-date holdouts can establish whether a direction filter generalizes.
    """
    data={}
    for side in ("OVER","UNDER"):
        cohort=[r for r in rows if r["side"]==side]
        result=summarize(cohort,MIN_MARKET_MARKETS,MIN_MARKET_DATES)
        n=len(cohort)
        result.update({
            "mean_signed_error_projection_minus_actual":
                round(sum(r["projection"]-r["actual"] for r in cohort)/n,3) if n else None,
            "mean_absolute_error":
                round(sum(abs(r["projection"]-r["actual"]) for r in cohort)/n,3) if n else None,
            "average_frozen_line_edge":
                round(sum(r["edge"] for r in cohort)/n,3) if n else None,
            "validated_selection_filter":False
        })
        data[side]=result
    return data

def analyze(records):
    observations=[]
    missing=defaultdict(int)
    for r in independent_rows(records):
        try:
            actual=finite(r.get("actual"))
            line=finite(r.get("line"))
            projection=forecast_values(r)["combined"]
            if actual is None or line is None or projection is None:
                missing["incomplete_quote_or_projection"]+=1;continue
            if actual==line:
                missing["push"]+=1;continue
            if line==projection:
                missing["no_direction"]+=1;continue
            stat=r.get("market")
            if stat not in MARKETS:continue
            start=utc(r["event_start"])
            date=start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            side="OVER" if projection>line else "UNDER"
            observations.append({"date":date,"game_date_eastern":date,
               "game":r.get("game"),"player":r.get("player"),
               "player_id":str(r.get("player_id")),"market":stat,
               "side":side,"edge":abs(projection-line),
               "actual":actual,"projection":projection,
               "won":int((actual>line)==(side=="OVER")),
               "source":r.get("settlement_source")})
        except (KeyError,TypeError,ValueError):
            missing["invalid_row"]+=1
    overall=summarize(observations)
    bymarket={}
    for m in MARKETS:
        subset=[o for o in observations if o["market"]==m]
        stat=summarize(subset,MIN_MARKET_MARKETS,MIN_MARKET_DATES)
        stat["by_direction"]=direction_error(subset)
        stat["edge_bands"]=[]
        for lo,hi in EDGE_BINS:
            group=[x for x in subset if lo<=x["edge"]<hi]
            data=summarize(group,MIN_MARKET_MARKETS,MIN_MARKET_DATES)
            data.update(edge_low=lo,edge_high=None if math.isinf(hi) else hi,
                label=f"{lo}–{hi if not math.isinf(hi) else '+'}" )
            stat["edge_bands"].append(data)
        bymarket[m]=stat
    return {"status":"RESEARCH_ONLY_NO_VALIDATED_BETTING_EDGE",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "production_predictions_unchanged":True,
        "production_probability_unchanged":True,
        "recommended_real_money_plays":0,
        "overall":overall,"by_market":bymarket,
        "overall_by_direction":direction_error(observations),
        "excluded":dict(missing),
        "requirements":{"minimum_total_markets":MIN_TOTAL_MARKETS,
          "minimum_total_game_dates":MIN_GAME_DATES,
          "minimum_per_market":MIN_MARKET_MARKETS,
          "minimum_per_market_dates":MIN_MARKET_DATES},
        "limitations":[
          "All edge thresholds are fixed in code BEFORE later evaluation, not fitted to these outcomes.",
          "Even meeting sample thresholds is not a claim of a verified betting edge.",
          "The per-market groups are not independent: same players, same games and PRA overlap.",
          "OVER/UNDER splits describe frozen historical behavior; neither side is a validated future selection filter.",
          "Must hold out full later game dates for true calibration, uncertainty and profitability.",
          "Historical market prices and sportsbook payouts can differ from PrizePicks.",
          "This diagnostic never changes the baseline AI or recommends money wagers."]}

def main():
    p=json.loads(LEDGER.read_text())
    r=analyze(p.get("records",[]))
    OUT.write_text(json.dumps(r,indent=2)+"\n")
    print("SELECTION-QUALITY RESEARCH",json.dumps({
        "overall":r["overall"],"markets":{m:{k:v for k,v in d.items() if k!="edge_bands"}
             for m,d in r["by_market"].items()}},sort_keys=True))

if __name__=="__main__":main()

"""Research-only forecast bias and underprojection diagnostic.

Uses earliest pre-tip saved sportsbook forecast per player/game/market.
Stratifies by information known at capture (projection tier, stored season
average, locked minutes risk) and not by future results. Opponent-vs-original
deltas are descriptive, NEVER causal contributions.
"""
import json
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean

try:
    from .model_performance import independent_rows,forecast_values,finite,utc
except ImportError:
    from model_performance import independent_rows,forecast_values,finite,utc

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUTPUT=ROOT/"docs/underprojection_research.json"
MARKETS=("PTS","REB","AST","PRA")
# Fixed pregame player-performance scale bins, not tuned on today's outcomes.
HIGH_PROJECTION={"PTS":25.,"REB":10.,"AST":8.,"PRA":40.}
MIN_DATES=5
MIN_MARKETS=50

def summarize(records):
    n=len(records)
    errors=[r["bias"] for r in records]
    dates={r["date"] for r in records}
    return {"observations":n,"distinct_event_dates":len(dates),
            "mean_signed_error_projection_minus_actual":round(mean(errors),3) if n else None,
            "mae":round(mean(abs(e) for e in errors),3) if n else None,
            "underprojection_count":sum(e<0 for e in errors),
            "overprojection_count":sum(e>0 for e in errors),
            "underprojection_share":round(sum(e<0 for e in errors)/n,4) if n else None,
            "sufficient_longitudinal_sample":n>=MIN_MARKETS and len(dates)>=MIN_DATES}

def history_baseline(row):
    info=row.get("season_average_challenger")
    if not isinstance(info,dict):return None
    if info.get("status")!="RESEARCH_CANDIDATE_NOT_VALIDATED":return None
    return finite(info.get("season_average"))

def report(records):
    chosen=independent_rows(records)
    rows=[]
    gaps=Counter()
    for r in chosen:
        market=str(r.get("market",""))
        if market not in MARKETS:continue
        projections=forecast_values(r)
        actual=finite(r.get("actual"))
        combined=projections["combined"]
        original=projections["original"]
        opponent=projections["opponent_aware"]
        if any(v is None or v<0 for v in (actual,combined,original,opponent)):
            gaps["missing_eligible_forecast_or_actual"]+=1
            continue
        event=utc(r["event_start"])
        baseline=history_baseline(r)
        season_gap=(combined-baseline)/baseline if baseline is not None and baseline>0 else None
        if season_gap is None:
            gaps["missing_frozen_current_season_baseline"]+=1
        risk=r.get("research_minutes_risk_v1")
        if not isinstance(risk,dict):gaps["missing_frozen_minutes_diagnostics"]+=1
        rows.append({"date":event.date().isoformat(),"player_id":str(r.get("player_id")),
            "player":str(r.get("player","")),"market":market,
            "game":str(r.get("game","")),"bias":combined-actual,
            "original_bias":original-actual,"opponent_bias":opponent-actual,
            "opponent_minus_original":opponent-original,
            "combined":combined,"actual":actual,"season_gap":season_gap,
            "season_baseline":baseline,
            "risk":risk if isinstance(risk,dict) else None})
    by_market={}
    for market in MARKETS:
        subset=[r for r in rows if r["market"]==market]
        high=[r for r in subset if r["combined"]>=HIGH_PROJECTION[market]]
        high_baseline=[r for r in subset if r["season_baseline"] is not None
                       and r["season_baseline"]>=HIGH_PROJECTION[market]]
        high_baseline_under=[r for r in high_baseline if r["season_gap"] is not None
                             and r["season_gap"]<=-.2]
        low=[r for r in subset if r["combined"]<HIGH_PROJECTION[market]]
        flagged_minutes=[r for r in subset if r["risk"] is not None and r["risk"].get("needs_manual_review") is True]
        stable_minutes=[r for r in subset if r["risk"] is not None and r["risk"].get("needs_manual_review") is False]
        opponent_lower=[r for r in subset if r["opponent_minus_original"]<=-1.]
        opponent_higher=[r for r in subset if r["opponent_minus_original"]>=1.]
        below_baseline=[r for r in subset if r["season_gap"] is not None and r["season_gap"]<=-.2]
        above_baseline=[r for r in subset if r["season_gap"] is not None and r["season_gap"]>=.2]
        by_market[market]={
            "all":summarize(subset),
            "high_forecast_tier":summarize(high),
            "high_frozen_season_baseline_tier":summarize(high_baseline),
            "high_baseline_and_projection_20pct_below":summarize(high_baseline_under),
            "other_forecast_tier":summarize(low),
            "pregame_forecast_20pct_below_frozen_season_avg":summarize(below_baseline),
            "pregame_forecast_20pct_above_frozen_season_avg":summarize(above_baseline),
            "high_tier_threshold":HIGH_PROJECTION[market],
            "frozen_minutes_review_flagged":summarize(flagged_minutes),
            "frozen_minutes_no_review_flags":summarize(stable_minutes),
            "opponent_model_1plus_below_original":summarize(opponent_lower),
            "opponent_model_1plus_above_original":summarize(opponent_higher),
            "opponent_vs_original":{
              "observations":len(subset),
              "mean_opponent_minus_original":round(mean(r["opponent_minus_original"] for r in subset),3) if subset else None,
              "original_bias":round(mean(r["original_bias"] for r in subset),3) if subset else None,
              "opponent_bias":round(mean(r["opponent_bias"] for r in subset),3) if subset else None}}
    # One-day player effects cannot be called systematic. Retain the worst
    # observed errors strictly as exploratory investigation examples.
    worst={}
    for market in MARKETS:
        group=[r for r in rows if r["market"]==market]
        worst[market]=[{
            "player":r["player"],"player_id":r["player_id"],
            "game":r["game"],"date":r["date"],
            "combined_projection":round(r["combined"],3),
            "actual":round(r["actual"],3),
            "projection_minus_actual":round(r["bias"],3),
            "opponent_minus_original":round(r["opponent_minus_original"],3),
            "pregame_vs_season_gap_pct":round(r["season_gap"]*100,2) if r["season_gap"] is not None else None
        } for r in sorted(group,key=lambda r:(r["bias"],r["player_id"]))[:8]]
    all_dates=len({r["date"] for r in rows})
    return {"status":"DESCRIPTIVE_UNDERPROJECTION_ROOT_CAUSE_RESEARCH_ONLY",
        "method":"EARLIEST_SETTLED_PRETIP_BOOK_QUOTE; FROZEN_FORECAST_TIER_AND_SEASON_CONTEXT",
        "independent_markets":len(rows),"distinct_event_dates":all_dates,
        "overall":summarize(rows),"by_market":by_market,
        "largest_observed_underprojections_by_market":worst,
        "data_quality":dict(gaps),
        "conclusions":{
            "systematic_underprojection_proven":False,
            "minutes_causality_proven":False,
            "opponent_adjustment_causality_proven":False,
            "ready_for_global_correction":False,
            "live_predictions_changed":False,
            "live_probabilities_changed":False},
        "limitations":[
            "Pregame forecast and frozen season-average tiers are fixed in advance; high actual outcomes do not determine the tiers.",
            "The fixed tier thresholds are research heuristics, not validated player-usage classifications.",
            "Opposing forecast differences are descriptive and do not establish opponent-caused errors.",
            "Recent or injury minutes correlations do not prove causality; incomplete frozen context is missing, never backfilled.",
            "PRA, PTS, REB and AST for a player/game are correlated. One game date is insufficient for longitudinal bias.",
            "Historical settlement feeds and player/team identity must be independently validated before acting on anomalous games.",
            "No changes to live pick selection, confidence values, projection formulas or model training."]}

def main():
    records=json.loads(LEDGER.read_text()).get("records",[])
    result=report(records)
    result["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print("Underprojection research:",json.dumps({"markets":result["independent_markets"],
        "distinct_dates":result["distinct_event_dates"],
        "bias_by_stat":{k:v["all"]["mean_signed_error_projection_minus_actual"]
                        for k,v in result["by_market"].items()}},sort_keys=True))

if __name__=="__main__":main()

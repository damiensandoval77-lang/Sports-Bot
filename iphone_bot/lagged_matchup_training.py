"""Chronological model experiment: fit lagged opportunity + matchup features.

2022-23/2023-24 training, 2024-25 validation, 2025-26 diagnostic.
2025-26 was previously inspected: NOT a fresh untouched confirmation set.
2026-27 prospective predictions must be frozen before their games start.

No NBAstuffer import. Observed box-score involvement proxy is NOT official USG%.
No game outcome or on-court defender matchup is a prediction-time input.
"""
import json
import math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error
import numpy as np
try:
    from .points_hit_probability import make_reference,bucket
except ImportError:
    from points_hit_probability import make_reference,bucket

try:
    from .offensive_involvement_holdout import load_history_with_box_context, predict
    from .expanded_matchup_research import build_team_games,defense_factor
except ImportError:
    from offensive_involvement_holdout import load_history_with_box_context,predict
    from expanded_matchup_research import build_team_games,defense_factor

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/lagged_opportunity_matchup_training.json"
TRAIN=("2022-23","2023-24")
VALIDATE="2024-25"
DIAGNOSTIC="2025-26"
COLS=("minutes_forecast","involvement_per_min","last3_points","last10_points",
      "prior_points_per_involvement","recent_fga_per_min","recent_fta_per_min",
      "recent_turnover_per_min","opponent_pace_factor","opponent_defense_factor",
      "last3_minutes","last10_minutes","history_count")
MAX_GAP=1

def make_rows(games):
    """Train only from same-team earlier dates; never a game being predicted."""
    by_player=defaultdict(list)
    for g in games:
        if all(g.get(k) is not None for k in ("id","team","date","season","PTS")):
            by_player[(g["season"],str(g["id"]),g["team"])].append(g)
    by_season=defaultdict(list)
    for g in games:by_season[g.get("season")].append(g)
    context={season:build_team_games(group,season) for season,group in by_season.items()}
    made=[]
    rejected=defaultdict(int)
    for (season,pid,team),player_games in by_player.items():
        prior=[]
        days=defaultdict(list)
        for g in player_games:days[g["date"]].append(g)
        for day in sorted(days):
            if len(days[day])!=1:
                rejected["ambiguous_player_date"]+=len(days[day]);continue
            actual=days[day][0]
            baseline=predict(prior)
            if baseline and actual.get("opponent") and all(actual.get(x) is not None for x in ("PTS","REB","AST")):
                prior10=prior[-10:]
                d=defense_factor(context[season],team,actual["opponent"],day)
                # A missing opponent sample is a missing feature, not a
                # fabricated league-average defense. Drop the training row.
                if d["status"]!="PRIOR_RECIPROCAL_TEAM_BOX_CONTEXT":
                    rejected["insufficient_opponent_history"]+=1
                else:
                    vol=sum(r["FGA"]+.44*r["FTA"]+r["TOV"] for r in prior)
                    pts=sum(r["PTS"] for r in prior)
                    if vol<=0:
                        rejected["zero_historical_opportunity"]+=1
                    else:
                        f={
                          "minutes_forecast":baseline["minutes_projection"],
                          "involvement_per_min":baseline["involvement_proxy"],
                          "last3_points":mean(r["PTS"] for r in prior[-3:]),
                          "last10_points":mean(r["PTS"] for r in prior10),
                          "prior_points_per_involvement":pts/vol,
                          "recent_fga_per_min":mean(r["FGA"]/r["MIN"] for r in prior10),
                          "recent_fta_per_min":mean(r["FTA"]/r["MIN"] for r in prior10),
                          "recent_turnover_per_min":mean(r["TOV"]/r["MIN"] for r in prior10),
                          "opponent_pace_factor":d["pace_factor"],
                          "opponent_defense_factor":d["defense_factor"],
                          "last3_minutes":mean(r["MIN"] for r in prior[-3:]),
                          "last10_minutes":mean(r["MIN"] for r in prior10),
                          "history_count":min(82,len(prior))}
                        if all(r.get(x) is not None and math.isfinite(float(r[x]))
                               for r in prior10 for x in ("REB","AST")):
                            for stat in ("REB","AST"):
                                f[stat+"_L3"]=mean(float(r[stat]) for r in prior[-3:])
                                f[stat+"_L10"]=mean(float(r[stat]) for r in prior10)
                                f[stat+"_PER_MIN_L10"]=mean(float(r[stat])/r["MIN"] for r in prior10)
                        else:
                            rejected["MISSING_REB_AST_HISTORY"]+=1
                            prior.append(actual)
                            continue
                        if all(math.isfinite(float(f[c])) for c in COLS):
                            made.append({"season":season,"date":day,
                                "game_id":actual.get("game_id"),"player_id":pid,
                                "team":team,"features":f,
                                "actual":float(actual["PTS"]),
                                "actual_reb":float(actual["REB"]),
                                "actual_ast":float(actual["AST"]),
                                "baseline":baseline["baseline"],
                                "involvement":baseline["challenger"]})
                        else:rejected["nonfinite_features"]+=1
            else:rejected["insufficient_player_history"]+=1
            prior.append(actual)
    return made,dict(rejected)

def _mae(rows,key):
    return round(mean(abs(x[key]-x["actual"]) for x in rows),4)

def evaluate(rows):
    sets={s:[r for r in rows if r["season"]==s] for s in (*TRAIN,VALIDATE,DIAGNOSTIC)}
    train=[r for s in TRAIN for r in sets[s]]
    valid=sets[VALIDATE]
    diagnostic=sets[DIAGNOSTIC]
    if len(train)<5000 or min(len(valid),len(diagnostic))<2000:
        raise ValueError("Insufficient historical season separated samples")
    def X(group):
        return np.array([[r["features"][c] for c in COLS] for r in group],dtype=float)
    y=np.array([r["actual"] for r in train],dtype=float)
    model=HistGradientBoostingRegressor(max_iter=120,max_depth=4,
       max_leaf_nodes=15,min_samples_leaf=70,learning_rate=.05,
       l2_regularization=10,early_stopping=False,random_state=2026)
    model.fit(X(train),y)
    def metrics(group):
        fitted=np.maximum(model.predict(X(group)),0)
        for row,p in zip(group,fitted):
            row["model"]=float(p)
        return {"n":len(group),"distinct_dates":len({r["date"] for r in group}),
                "baseline_mae":_mae(group,"baseline"),
                "involvement_mae":_mae(group,"involvement"),
                "trained_matchup_mae":_mae(group,"model"),
                "model_minus_involvement_mae":round(_mae(group,"model")-_mae(group,"involvement"),4)}
    # Probability reference is restricted to distinct 2024-25 validation
    # games. Never use 2025-26 diagnostic outcomes in the live residual pool.
    validation_prediction=np.maximum(model.predict(X(valid)),0)
    probability_reference=make_reference(validation_prediction,[r["actual"] for r in valid])
    # Retrospective only: assess probability diagnostic on synthetic,
    # clearly NON-PRIZEPICKS half-point lines. This measures distribution
    # fit but is not an observed pick'em hit rate.
    diagnostic_prediction=np.maximum(model.predict(X(diagnostic)),0)
    brier_sum=0.;scored=0
    global_errors=np.sort(np.asarray(probability_reference["residuals"]))
    bucket_errors={k:np.sort(np.asarray(v)) for k,v in probability_reference["by_projection_bucket"].items()}
    for row, projected in zip(diagnostic,diagnostic_prediction):
        fake_line=float(np.floor(projected)+.5)
        # Discrete points above a half-point line are equivalent to
        # (forecast + residual)>line; use the empirical CDF exactly.
        threshold=fake_line-projected
        local=bucket_errors.get(bucket(projected),global_errors)
        p_local=(len(local)-np.searchsorted(local,threshold,side="right"))/len(local)
        p_global=(len(global_errors)-np.searchsorted(global_errors,threshold,side="right"))/len(global_errors)
        p_over=.85*p_local+.15*p_global
        outcome=int(row["actual"]>fake_line)
        brier_sum+=(p_over-outcome)**2
        scored+=1
    probability_diagnostic={"sample_size":scored,
        "synthetic_half_point_line_brier":round(brier_sum/scored,5),
        "line_source":"SYNTHETIC_MODEL_NEARBY_HALF_POINT_NOT_PRIZEPICKS",
        "calibrated_for_live_betting":False}
    # Freeze the exact model fitted only on earlier seasons for future,
    # independently dated prospective research capture.
    import joblib
    model_file=ROOT/"models/nba/research/lagged_matchup_2022_24.joblib"
    model_file.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({"model":model,"columns":COLS,"training_seasons":TRAIN,
                 "validation_season":VALIDATE,"probability_reference":probability_reference,
                 "research_only":True,
                 "production_modified":False},model_file)
    return {"status":"HISTORICAL_LAGGED_MATCHUP_TRAINING_COMPLETE",
       "training_seasons":TRAIN,"train_rows":len(train),
       "validation_season":VALIDATE,"validation":metrics(valid),
       "diagnostic_seen_season":DIAGNOSTIC,"diagnostic":metrics(diagnostic),
       "feature_columns":COLS,
       "frozen_model_artifact":"models/nba/research/lagged_matchup_2022_24.joblib",
       "probability_reference":{"source":probability_reference["source"],
          "sample_size":probability_reference["sample_size"],
          "bucket_sizes":{k:len(v) for k,v in probability_reference["by_projection_bucket"].items()}},
       "probability_diagnostic":probability_diagnostic,
       "model_type":"HIST_GRADIENT_BOOSTING_FROZEN_HYPERPARAMETERS",
       "no_official_usage_pct":True,
       "no_verified_pretip_injuries":True,
       "no_verified_position_context":True,
       "no_sportsbook_lines":True,
       "no_live_predictions":True,"production_modified":False,
       "automatic_promotion":False,
       "limitations":["2025-26 is a previously inspected diagnostic sample, not a fresh holdout.",
          "2024-25 is a separated model evaluation sample, but features were designed after viewing 2025-26.",
          "Historical same-season opponent data uses only strictly earlier games.",
          "No true USG%, teammate OUT labels, or G/F/C role changes are inferred.",
          "Next mandatory gate: freeze new 2026-27 pregame forecasts, then grade future outcomes.",
          "A lower MAE does not demonstrate a profitable wager or calibrated hit probability."]}

def main():
    games,rejected=load_history_with_box_context()
    rows,excluded=make_rows(games)
    result=evaluate(rows)
    result["source_rejections"]=rejected
    result["feature_rejections"]=excluded
    result["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print("LAGGED_MATCHUP_RESULTS",json.dumps({
       "training":result["train_rows"],
       "validation":result["validation"],
       "diagnostic":result["diagnostic"]}),flush=True)

if __name__=="__main__":
    main()

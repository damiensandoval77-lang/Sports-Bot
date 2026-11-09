"""Train rebound and assist challengers on older seasons; PRA is exact sum.

Existing validated points model is reused without retuning. Match all market
residuals on the SAME 2024-25 player/game observation, preserving correlation.
No 2025-26/2026-27 fit, no synthetic PrizePicks quotes, no claimed calibration.
"""
import json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
try:
    from .lagged_matchup_training import make_rows,COLS,TRAIN,VALIDATE,DIAGNOSTIC
    from .offensive_involvement_holdout import load_history_with_box_context
except ImportError:
    from lagged_matchup_training import make_rows,COLS,TRAIN,VALIDATE,DIAGNOSTIC
    from offensive_involvement_holdout import load_history_with_box_context

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"models/nba/research/lagged_matchup_all_markets.joblib"
REPORT=ROOT/"docs/lagged_matchup_all_market_validation.json"
EXTRA=("REB_L3","REB_L10","REB_PER_MIN_L10","AST_L3","AST_L10","AST_PER_MIN_L10")
FEATURES=tuple(COLS)+EXTRA
MARKETS=("PTS","REB","AST","PRA")

def train(rows,points_pack):
    if tuple(points_pack.get("columns") or ())!=tuple(COLS) or tuple(points_pack.get("training_seasons") or ())!=tuple(TRAIN):
        raise ValueError("Points model mismatch")
    by_season={s:[r for r in rows if r["season"]==s] for s in (*TRAIN,VALIDATE,DIAGNOSTIC)}
    train_rows=[r for s in TRAIN for r in by_season[s]]
    val=by_season[VALIDATE]
    diag=by_season[DIAGNOSTIC]
    if min(len(train_rows),len(val),len(diag))<2000:raise ValueError("Inadequate real historical data")
    def X(data):return np.asarray([[r["features"][k] for k in FEATURES] for r in data],dtype=float)
    def XP(data):return np.asarray([[r["features"][k] for k in COLS] for r in data],dtype=float)
    xtrain=X(train_rows)
    models={"PTS":points_pack["model"]}
    for stat,target in (("REB","actual_reb"),("AST","actual_ast")):
        m=HistGradientBoostingRegressor(max_iter=120,max_depth=4,max_leaf_nodes=15,
             min_samples_leaf=70,learning_rate=.05,l2_regularization=10,
             early_stopping=False,random_state=2026)
        m.fit(xtrain,np.asarray([r[target] for r in train_rows]))
        models[stat]=m
    def forecasts(data):
        features=X(data)
        out={"PTS":np.maximum(0,models["PTS"].predict(XP(data))),
             "REB":np.maximum(0,models["REB"].predict(features)),
             "AST":np.maximum(0,models["AST"].predict(features))}
        out["PRA"]=out["PTS"]+out["REB"]+out["AST"]
        return out
    def actuals(data):
        a={"PTS":np.asarray([r["actual"] for r in data]),
           "REB":np.asarray([r["actual_reb"] for r in data]),
           "AST":np.asarray([r["actual_ast"] for r in data])}
        a["PRA"]=a["PTS"]+a["REB"]+a["AST"]
        return a
    pv,pa=forecasts(val),actuals(val)
    pd,da=forecasts(diag),actuals(diag)
    residuals=np.column_stack([pa[s]-pv[s] for s in ("PTS","REB","AST")])
    if residuals.shape[0]<1000 or not np.isfinite(residuals).all():
        raise ValueError("Invalid out-of-training residual reference")
    def metrics(preds,truth):
        return {s:{"mae":round(float(mean_absolute_error(truth[s],preds[s])),4),
                   "n":len(truth[s])} for s in MARKETS}
    pack={"research_only":True,"calibrated":False,"training_seasons":TRAIN,
          "feature_columns":FEATURES,"points_feature_columns":COLS,
          "models":models,"validation_residual_triplets":residuals,
          "validation_year":VALIDATE,
          "frozen_model_policy":"PTS_existing_2022_24_REB_AST_new_2022_24_PRA_sum"}
    result={"status":"MULTIMARKET_HISTORICAL_VALIDATION",
       "train_rows":len(train_rows),"validation_dates":len({r["date"] for r in val}),
       "validation":metrics(pv,pa),"diagnostic_seen_year":metrics(pd,da),
       "validation_season":VALIDATE,"diagnostic_season":DIAGNOSTIC,
       "probability_reference_rows":residuals.shape[0],
       "pra_projection_exact_sum":True,"correlated_residuals":True,
       "live_calibration_verified":False,"production_replaced":False}
    return pack,result

def main():
    rows,raw_rejections=load_history_with_box_context()
    prepared,rejections=make_rows(rows)
    old=joblib.load(ROOT/"models/nba/research/lagged_matchup_2022_24.joblib")
    pack,report=train(prepared,old)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(pack,OUTPUT)
    report["source_rejections"]=raw_rejections
    report["feature_rejections"]=rejections
    report["created_at"]=datetime.now(timezone.utc).isoformat()
    REPORT.write_text(json.dumps(report,indent=2)+"\n")
    print("MULTIMARKET_MATCHUP_VALIDATION",json.dumps({
      "train":report["train_rows"],"validation":report["validation"],
      "diagnostic":report["diagnostic_seen_year"]}),flush=True)

if __name__=="__main__":main()

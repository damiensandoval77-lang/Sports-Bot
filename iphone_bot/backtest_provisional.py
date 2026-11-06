"""Research-only out-of-time NBA over/under proxy backtest.

A 60/20/20 chronological split trains regression, estimates residual distribution
on validation games, then scores untouched test games. Proxy lines are derived
from rolling statistics; NEVER label them as historical sportsbook odds.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from math import floor
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, brier_score_loss

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/nba/processed/training_dataset.csv"
OUT=ROOT/"models/nba/provisional/backtest"
TARGETS=("PTS","REB","AST","PRA")
BASE=("MIN_L5","MIN_L10","MIN_Season","DAYS_REST","IS_HOME",
      "IS_B2B","IS_FRESH","GAMES_7D","IS_4_IN_6")
STATS=("PTS","REB","AST","FGA","FG3A","TOV")
FEATURES=BASE+tuple(f"{s}_{w}" for s in STATS for w in ("L5","L10","Season"))

def empirical_probability(sorted_residuals, predicted, line):
    # Strictly greater than a half-point line (no push for integer box-score props).
    threshold=line-predicted
    n=len(sorted_residuals)
    return np.clip((n-np.searchsorted(sorted_residuals,threshold,side="right"))/n,0.01,0.99)

def ece(prob, actual, bins=10):
    edges=np.linspace(0,1,bins+1)
    total=0.
    for k in range(bins):
        group=(prob>=edges[k]) & ((prob<edges[k+1]) if k<bins-1 else (prob<=edges[k+1]))
        if group.any():
            total+=group.mean()*abs(prob[group].mean()-actual[group].mean())
    return float(total)

def main():
    df=pd.read_csv(DATA,low_memory=False)
    df["GAME_DATE"]=pd.to_datetime(df["GAME_DATE"],errors="raise")
    df=df.sort_values(["GAME_DATE","PLAYER_ID"]).reset_index(drop=True)
    cols=[x for x in FEATURES if x in df.columns]
    if len(cols)<12: raise ValueError("Insufficient lagged features")
    dates=df["GAME_DATE"].drop_duplicates().sort_values().to_numpy()
    if len(dates)<150: raise ValueError("Insufficient game dates")
    d1=pd.Timestamp(dates[int(len(dates)*.6)])
    d2=pd.Timestamp(dates[int(len(dates)*.8)])
    train=df["GAME_DATE"]<d1
    valid=(df["GAME_DATE"]>=d1)&(df["GAME_DATE"]<d2)
    test=df["GAME_DATE"]>=d2
    if min(train.sum(),valid.sum(),test.sum())<1000:
        raise ValueError("Insufficient chronological split rows")
    X=df[cols].apply(pd.to_numeric,errors="coerce")
    medians=X.loc[train].median().fillna(0)
    X=X.replace([np.inf,-np.inf],np.nan).fillna(medians).fillna(0)
    OUT.mkdir(parents=True,exist_ok=True)
    results=[]
    for target in TARGETS:
        y=pd.to_numeric(df[target],errors="coerce")
        tr=train & y.notna()
        va=valid & y.notna()
        te=test & y.notna()
        if min(tr.sum(),va.sum(),te.sum())<1000: raise ValueError("Missing target rows "+target)
        model=HistGradientBoostingRegressor(max_iter=180,max_leaf_nodes=21,
            max_depth=5,min_samples_leaf=65,learning_rate=.055,
            l2_regularization=4.,early_stopping=False,random_state=42)
        model.fit(X.loc[tr],y.loc[tr])
        pred_val=np.maximum(0,model.predict(X.loc[va]))
        pred_test=np.maximum(0,model.predict(X.loc[te]))
        residual=np.sort((y.loc[va].to_numpy()-pred_val).astype(float))
        # A deliberately artificial non-market line, 0.5 above its floored L10 mean.
        if f"{target}_L10" in X:
            proxy=X.loc[te,f"{target}_L10"].to_numpy()
        elif target=="PRA":
            proxy=(X.loc[te,"PTS_L10"]+X.loc[te,"REB_L10"]+
                   X.loc[te,"AST_L10"]).to_numpy()
        else:
            raise ValueError("Missing baseline for "+target)
        proxy_line=np.floor(np.maximum(proxy,0))+.5
        actual=(y.loc[te].to_numpy()>proxy_line).astype(int)
        probabilities=empirical_probability(residual,pred_test,proxy_line)
        predicted_side=(probabilities>=.5).astype(int)
        correct=(predicted_side==actual)
        baseline_prob=np.full(len(actual),actual.mean())
        result={
            "target":target,
            "train_rows":int(tr.sum()),"validation_rows":int(va.sum()),
            "test_rows":int(te.sum()),
            "test_mae":round(float(mean_absolute_error(y.loc[te],pred_test)),4),
            "proxy_hit_rate_pct":round(float(correct.mean()*100),2),
            "proxy_brier":round(float(brier_score_loss(actual,probabilities)),4),
            "constant_base_rate_brier":round(float(brier_score_loss(actual,baseline_prob)),4),
            "proxy_expected_calibration_error":round(ece(probabilities,actual),4),
            "mean_predicted_over_probability":round(float(probabilities.mean()),4),
            "actual_over_frequency":round(float(actual.mean()),4)
        }
        (OUT/f"{target}_reliability.csv").write_text(
            "predicted_probability,actual_over,proxy_line,prediction\n"+
            "".join(f"{p:.6f},{a},{l:.1f},{v:.4f}\n" for p,a,l,v in
                    zip(probabilities,actual,proxy_line,pred_test)))
        results.append(result)
        print(json.dumps(result),flush=True)
    report={
       "created_at":datetime.now(timezone.utc).isoformat(),
       "train_end":str(df.loc[train,"GAME_DATE"].max().date()),
       "validation_start":str(d1.date()),"validation_end":str(df.loc[valid,"GAME_DATE"].max().date()),
       "test_start":str(d2.date()),"test_end":str(df.loc[test,"GAME_DATE"].max().date()),
       "data_rows":int(len(df)), "features":cols, "markets":"NONE",
       "line_type":"SYNTHETIC_ROLLING_L10_HALF_POINT",
       "status":"RESEARCH_ONLY_NOT_A_SPORTSBOOK_BACKTEST",
       "note":"Proxy lines are floor(prior 10 game average)+0.5, NOT real bookmaker or PrizePicks lines.",
       "limitations":[
           "Not real sports betting historical lines, odds, payout or EV.",
           "Model split by date; residual probabilities calibrated on validation period only.",
           "Underlying feature engineering is provisional and requires separate leakage audit.",
           "Position and personal-foul data are missing from the source.",
           "No guarantee these findings transfer to actual betting lines or live games."
       ], "metrics":results
    }
    (OUT/"backtest_report.json").write_text(json.dumps(report,indent=2))
    print("Proxy backtest complete; NO real sportsbook lines used",flush=True)

if __name__=="__main__":
    main()

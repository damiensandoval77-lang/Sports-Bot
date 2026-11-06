"""Chronological challenger: does opponent team defense improve projections?

Uses only pre-game opponent allowance features, compared to an identical
baseline on a held-out chronological slice. Deliberately does NOT export a
live model or claim real-betting probabilities.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, brier_score_loss
from defense_training import add_historical_defense, COLS

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/nba/raw/raw_game_logs.csv"
TRAINING=ROOT/"data/nba/processed/training_dataset.csv"
OUT=ROOT/"models/nba/defense_challenger"
BASE=("MIN_L5","MIN_L10","MIN_Season","DAYS_REST","IS_HOME",
      "IS_B2B","IS_FRESH","GAMES_7D","IS_4_IN_6")
STATS=("PTS","REB","AST","FGA","FG3A","TOV")
FEATURES=BASE+tuple(f"{s}_{w}" for s in STATS for w in ("L5","L10","Season"))
TARGETS=("PTS","REB","AST","PRA")

def model():
    return HistGradientBoostingRegressor(max_iter=140,max_depth=5,
        max_leaf_nodes=21,min_samples_leaf=70,learning_rate=.055,
        l2_regularization=4,early_stopping=False,random_state=42)

def probability(residuals,pred,line):
    """Empirical validation residual CDF, NOT bookmaker-calibrated odds."""
    r=np.sort(np.asarray(residuals,float))
    return np.clip((len(r)-np.searchsorted(r,np.asarray(line)-pred,side="right"))/len(r),.01,.99)

def main():
    raw=pd.read_csv(RAW,dtype={"GAME_ID":"string"},low_memory=False)
    df=pd.read_csv(TRAINING,dtype={"GAME_ID":"string"},low_memory=False)
    for label,data in (("raw",raw),("training",df)):
        if not {"SEASON_ID","GAME_ID","TEAM_ABBREVIATION","GAME_DATE"}.issubset(data):
            raise ValueError(f"{label}: game/team key missing")
    df=add_historical_defense(df,raw)
    # Identical predictions across every target can mean the opponent inputs
    # are all NaN and imputed to constants. Reject that silently broken test.
    coverage={}
    for feature in COLS:
        values=pd.to_numeric(df[feature],errors="coerce")
        coverage[feature]={"coverage_pct":round(float(values.notna().mean()*100),2),
                           "distinct":int(values.nunique(dropna=True))}
    print("Defensive feature diagnostics:",json.dumps(coverage),flush=True)
    if any(v["coverage_pct"]<50 or v["distinct"]<8 for v in coverage.values()):
        raise ValueError("Opponent challenger lacks sufficient non-constant matchup data; comparison invalid")
    df["GAME_DATE"]=pd.to_datetime(df["GAME_DATE"])
    df=df.sort_values(["GAME_DATE","PLAYER_ID"]).reset_index(drop=True)
    dates=np.sort(df.GAME_DATE.unique())
    if len(dates)<150:raise ValueError("Too few historical dates")
    first=pd.Timestamp(dates[int(len(dates)*.60)])
    second=pd.Timestamp(dates[int(len(dates)*.80)])
    train=df.GAME_DATE<first
    calibration=(df.GAME_DATE>=first)&(df.GAME_DATE<second)
    test=df.GAME_DATE>=second
    if train.sum()<10000 or calibration.sum()<2000 or test.sum()<2000:
        raise ValueError("Chronological slices too small")
    baseline=[x for x in FEATURES if x in df.columns]
    challenger=baseline+list(COLS)
    report=[]
    for target in TARGETS:
        results={}
        for version,cols in (("baseline",baseline),("opponent_challenger",challenger)):
            matrix=df[cols].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
            fill=matrix.loc[train].median().fillna(0)
            matrix=matrix.fillna(fill).fillna(0)
            predictor=model()
            predictor.fit(matrix.loc[train],df.loc[train,target])
            pred_val=np.maximum(0,predictor.predict(matrix.loc[calibration]))
            pred_test=np.maximum(0,predictor.predict(matrix.loc[test]))
            ytest=df.loc[test,target].to_numpy(dtype=float)
            errors=df.loc[calibration,target].to_numpy(dtype=float)-pred_val
            # Proxy lines test mathematical probability plumbing only, not
            # the profitability of real sportsbooks or PrizePicks.
            if target=="PRA":
                proxy=(df.loc[test,"PTS_L10"]+df.loc[test,"REB_L10"]+
                       df.loc[test,"AST_L10"]).to_numpy(dtype=float)
            else:
                proxy=df.loc[test,f"{target}_L10"].to_numpy(dtype=float)
            proxy=np.floor(np.maximum(proxy,0))+.5
            valid=np.isfinite(proxy)&np.isfinite(ytest)
            p=probability(errors,pred_test[valid],proxy[valid])
            actual=(ytest[valid]>proxy[valid]).astype(int)
            results[version]={
                "mae":round(float(mean_absolute_error(ytest,pred_test)),4),
                "proxy_brier":round(float(brier_score_loss(actual,p)),4),
                "proxy_rows":int(valid.sum()),
                "avg_over_probability":round(float(p.mean()),4)}
        base=results["baseline"];other=results["opponent_challenger"]
        report.append({"stat":target,**results,
            "mae_improvement":round(base["mae"]-other["mae"],4),
            "proxy_brier_improvement":round(base["proxy_brier"]-other["proxy_brier"],4),
            "passed_mae":bool(other["mae"]<base["mae"]),
            "passed_proxy_brier":bool(other["proxy_brier"]<base["proxy_brier"])})
        print(json.dumps(report[-1]),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    out={"generated_at":datetime.now(timezone.utc).isoformat(),
       "status":"RESEARCH_CHALLENGER_NOT_DEPLOYED",
       "dataset_rows":len(df),"train_end":str(first.date()),
       "validation_end":str(second.date()),"test_start":str(second.date()),
       "new_features":list(COLS),"feature_coverage":coverage,
       "lines":"SYNTHETIC_L10_PROXY_NOT_REAL_SPORTSBOOK_ODDS",
       "probability_method":"validation residual empirical CDF, unvalidated on real lines",
       "metrics":report,
       "note":"Holdout results are historical. No live model promotion or betting confidence until prospective real-line calibration and independent validation."}
    (OUT/"report.json").write_text(json.dumps(out,indent=2)+"\n")
    print("Challenger research complete; no production model changed",flush=True)

if __name__=="__main__":main()

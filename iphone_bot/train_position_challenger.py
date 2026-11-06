"""Evaluate whether position-specific opponent defense improves NBA props.

No production model promotion. Both candidates evaluated on identical
chronological rows and same training-only imputation. DvP uses G/F/C
player-average allowances (not primary defender matchup).
"""
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from defense_training import add_historical_defense,COLS
from position_defense import fetch_positions,positional_features,merge_training,DVP_COLS
from train_defense_challenger import FEATURES,TARGETS,model
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"models/nba/position_challenger"

def main():
    raw=pd.read_csv(ROOT/"data/nba/raw/raw_game_logs.csv",dtype={"GAME_ID":"string"},low_memory=False)
    training=pd.read_csv(ROOT/"data/nba/processed/training_dataset.csv",dtype={"GAME_ID":"string"},low_memory=False)
    positions=fetch_positions()
    position_games=positional_features(raw,positions)
    df=merge_training(add_historical_defense(training,raw),position_games)
    df=df[df["SEASON_ID"].isin(("2024-25","2025-26"))].copy()
    df=df[df["POSITION_ROLE"].notna()].copy()
    coverage={name:round(float(df[name].notna().mean())*100,2) for name in DVP_COLS}
    distinct={name:int(df[name].nunique(dropna=True)) for name in DVP_COLS}
    print("Positional DvP coverage:",json.dumps(coverage),flush=True)
    print("Positional DvP unique values:",json.dumps(distinct),flush=True)
    if len(df)<15000 or min(coverage.values())<45 or any(v<5 for v in distinct.values()):
        raise ValueError("Too little valid DvP data to compare models safely")
    df["GAME_DATE"]=pd.to_datetime(df["GAME_DATE"])
    df=df.sort_values(["GAME_DATE","PLAYER_ID"]).reset_index(drop=True)
    dates=np.sort(df.GAME_DATE.unique())
    if len(dates)<130:raise ValueError("Not enough historical dates")
    train_end=pd.Timestamp(dates[int(len(dates)*.60)])
    valid_end=pd.Timestamp(dates[int(len(dates)*.80)])
    tr=df.GAME_DATE<train_end
    va=(df.GAME_DATE>=train_end)&(df.GAME_DATE<valid_end)
    te=df.GAME_DATE>=valid_end
    if min(int(tr.sum()),int(va.sum()),int(te.sum()))<1500:
        raise ValueError("Not enough date-separated observations")
    cols=[x for x in FEATURES if x in df.columns]+list(COLS)
    variants={"team_defense_only":cols,"team_plus_position_defense":cols+list(DVP_COLS)}
    results=[]
    for stat in TARGETS:
        performance={}
        for name,features in variants.items():
            X=df[features].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
            med=X.loc[tr].median().fillna(0)
            X=X.fillna(med).fillna(0)
            m=model()
            m.fit(X.loc[tr],pd.to_numeric(df.loc[tr,stat]))
            pred=np.maximum(0,m.predict(X.loc[te]))
            actual=pd.to_numeric(df.loc[te,stat]).to_numpy()
            performance[name]={"mae":round(float(mean_absolute_error(actual,pred)),4),
                               "test_rows":int(te.sum())}
        gain=performance["team_defense_only"]["mae"]-performance["team_plus_position_defense"]["mae"]
        results.append({"market":stat,**performance,"mae_improvement":round(gain,4),
                        "position_model_better":bool(gain>0)})
        print("POSITION RESULT:",json.dumps(results[-1]),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    report={"generated_at":datetime.now(timezone.utc).isoformat(),
            "status":"POSITION_RESEARCH_NOT_DEPLOYED",
            "position_granularity":"G/F/C coarse source listed positions; not actual defensive matchup assignments",
            "historical_seasons":["2024-25","2025-26"],
            "training_rows":int(tr.sum()),"validation_rows":int(va.sum()),"test_rows":int(te.sum()),
            "training_end_exclusive":str(train_end.date()),
            "test_from":str(valid_end.date()),
            "dvp_feature_coverage_pct":coverage,"metrics":results,
            "note":"Descriptive DvP feature challenger; no real sportsbook profitability or calibrated hit probabilities."}
    (OUT/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Position defense research finished, not promoted",flush=True)

if __name__=="__main__":main()

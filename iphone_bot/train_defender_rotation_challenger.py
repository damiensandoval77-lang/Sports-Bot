"""Fourth offline challenger: opponent's probable defensive rotation signals.

Compares identical chronological rows using team defense, and team defense +
individual defender-boxscore aggregation, never direct defender assignments.
No real sportsbook lines, no automated live promotion.
"""
import json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from defense_training import add_historical_defense,COLS
from defender_rotation_features import attach_rotation_to_training,FEATURE_COLS
from train_defense_challenger import FEATURES,TARGETS,model

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"models/nba/defender_rotation_challenger"

def main():
    raw=pd.read_csv(ROOT/"data/nba/raw/raw_game_logs.csv",
                    dtype={"GAME_ID":"string"},low_memory=False)
    original=pd.read_csv(ROOT/"data/nba/processed/training_dataset.csv",
                         dtype={"GAME_ID":"string"},low_memory=False)
    df=attach_rotation_to_training(add_historical_defense(original,raw),raw)
    date=pd.to_datetime(df["GAME_DATE"])
    df=df.assign(GAME_DATE=date).sort_values(["GAME_DATE","PLAYER_ID"]).reset_index(drop=True)
    dates=np.sort(df.GAME_DATE.unique())
    if len(dates)<150:raise ValueError("Insufficient distinct dates")
    first=pd.Timestamp(dates[int(len(dates)*.6)])
    second=pd.Timestamp(dates[int(len(dates)*.8)])
    train=df.GAME_DATE<first
    validation=(df.GAME_DATE>=first)&(df.GAME_DATE<second)
    test=df.GAME_DATE>=second
    if min(int(train.sum()),int(validation.sum()),int(test.sum()))<1500:
        raise ValueError("Insufficient chronological rows")
    coverage={}
    for f in FEATURE_COLS:
        values=pd.to_numeric(df[f],errors="coerce")
        coverage[f]={"coverage_pct":round(float(values.notna().mean()*100),2),
                     "distinct":int(values.nunique(dropna=True))}
    print("Defender rotation coverage:",json.dumps(coverage),flush=True)
    if min(v["coverage_pct"] for v in coverage.values())<55:
        raise ValueError("Opponent player-level defensive features insufficient for test")
    if any(v["distinct"]<3 for v in coverage.values()):
        raise ValueError("Opponent defensive features are nonvarying; cannot compare")
    base=[col for col in FEATURES if col in df.columns]+list(COLS)
    variants={"team_defense_only":base,
              "team_plus_defender_rotation":base+list(FEATURE_COLS)}
    metrics=[]
    for stat in TARGETS:
        result={"market":stat,"test_rows":int(test.sum()),"variants":{}}
        for variant,cols in variants.items():
            X=df[cols].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
            fill=X.loc[train].median().fillna(0)
            X=X.fillna(fill).fillna(0)
            reg=model()
            reg.fit(X.loc[train],pd.to_numeric(df.loc[train,stat]))
            predicted=np.maximum(0,reg.predict(X.loc[test]))
            observed=pd.to_numeric(df.loc[test,stat]).to_numpy()
            result["variants"][variant]={"mae":round(float(mean_absolute_error(observed,predicted)),4)}
        gain=result["variants"]["team_defense_only"]["mae"]-result["variants"]["team_plus_defender_rotation"]["mae"]
        result["mae_improvement"]=round(float(gain),4)
        result["defender_features_better"]=bool(gain>0)
        metrics.append(result)
        print("DEFENDER ROTATION RESULT:",json.dumps(result),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    report={
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "status":"INDIVIDUAL_DEFENDER_RESEARCH_NOT_DEPLOYED",
      "features":list(FEATURE_COLS),
      "defender_signal":"Opposing team's likely rotation: past player STL/BLK/DREB per36, minutes weighted; no identified direct matchup",
      "training_rows":int(train.sum()),"validation_rows":int(validation.sum()),
      "test_rows":int(test.sum()),"test_from":str(second.date()),
      "coverage":coverage,"metrics":metrics,
      "limitations":[
         "Past minutes suggest potential rotation only; injuries, starters and availability unverified.",
         "Steals, blocks and defensive rebounds are imperfect proxies for defensive effectiveness.",
         "No matchup tracking, contested FG%, opponent FG% guarded or verified primary defenders.",
         "Results use completed historical boxscores, not bookmaker prices or PrizePicks returns.",
         "No live models, probabilities or recommendations are updated."
      ]}
    (OUT/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Defender rotation research finished: no production model changes",flush=True)

if __name__=="__main__":main()

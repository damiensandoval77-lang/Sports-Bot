"""Fit opponent-aware models for shadow-only, forward NBA evaluation.

The base model displayed on the public board is not modified. Trained only
with lagged box-score features and prior-game opponent TEAM totals. No betting
probabilities, injury claims or expected-value estimates are emitted.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from defense_training import add_historical_defense,COLS
from train_defense_challenger import FEATURES,TARGETS,model

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"models/nba/defense_shadow"

def main():
    raw=pd.read_csv(ROOT/"data/nba/raw/raw_game_logs.csv",dtype={"GAME_ID":"string"},low_memory=False)
    training=pd.read_csv(ROOT/"data/nba/processed/training_dataset.csv",dtype={"GAME_ID":"string"},low_memory=False)
    df=add_historical_defense(training,raw)
    cols=[x for x in FEATURES if x in df.columns]+list(COLS)
    missing=[x for x in COLS if not pd.to_numeric(df[x],errors="coerce").notna().any()]
    if missing:raise ValueError("Cannot train shadow with missing defensive features: "+str(missing))
    dates=pd.to_datetime(df["GAME_DATE"])
    # Fit only through most recent historical season (pre-current 2026-27).
    if dates.max()>=pd.Timestamp("2026-10-01"):
        raise ValueError("Shadow training includes current-season/future records unexpectedly")
    X=df[cols].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
    fills=X.median().fillna(0)
    X=X.fillna(fills).fillna(0)
    OUT.mkdir(parents=True,exist_ok=True)
    for stat in TARGETS:
        y=pd.to_numeric(df[stat],errors="coerce")
        valid=y.notna()
        m=model()
        m.fit(X.loc[valid],y.loc[valid])
        joblib.dump({"model":m,"features":cols,"fill_values":fills.to_dict(),
                     "target":stat,"status":"SHADOW_ONLY_NOT_CALIBRATED",
                     "training_through":str(dates.max().date())},
                    OUT/f"{stat}_model.joblib",compress=3)
        print("Shadow model trained:",stat,int(valid.sum()),"rows",flush=True)
    (OUT/"metadata.json").write_text(json.dumps({
        "created_at":datetime.now(timezone.utc).isoformat(),
        "status":"SHADOW_ONLY_NOT_CALIBRATED",
        "training_through":str(dates.max().date()),
        "features":cols,
        "note":"Distinct training recipe from public baseline; holdout comparison is research only. Not real-line calibrated."
    },indent=2)+"\n")

if __name__=="__main__":main()

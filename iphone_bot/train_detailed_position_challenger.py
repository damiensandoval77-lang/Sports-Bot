"""Compare high-granularity DvP feature blocks on identical historical rows.

No market hit-rate claims: MAE uses completed box scores, not observed lines.
All candidates share exactly the same chronological train/validation/test
splits; historical listed positions are not measured guarding assignments.
"""
import json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from defense_training import add_historical_defense,COLS
from detailed_position_defense import (
    fetch_exact_positions,build_detailed_dvp,merge_detailed,DETAILED_COLS,ROLES)
from train_defense_challenger import FEATURES,TARGETS,model

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"models/nba/detailed_position_challenger"

def main():
    raw=pd.read_csv(ROOT/"data/nba/raw/raw_game_logs.csv",dtype={"GAME_ID":"string"},low_memory=False)
    train_data=pd.read_csv(ROOT/"data/nba/processed/training_dataset.csv",dtype={"GAME_ID":"string"},low_memory=False)
    lookup,sources=fetch_exact_positions()
    detailed=build_detailed_dvp(raw,lookup)
    df=merge_detailed(add_historical_defense(train_data,raw),detailed)
    df=df[df["SEASON_ID"].isin(("2024-25","2025-26"))].copy()
    coverage={"exact_position_pct":round(float(df.EXACT_ROLE.notna().mean()*100),2)}
    coverage.update({col:round(float(df[col].notna().mean()*100),2) for col in DETAILED_COLS})
    roles=df.EXACT_ROLE.value_counts(dropna=False).to_dict()
    print("Detailed position role sample counts:",json.dumps({str(k):int(v) for k,v in roles.items()}),flush=True)
    print("Detailed positional feature coverage:",json.dumps(coverage),flush=True)
    # Don't silently back-fill G/F to fabricated PG/SG/SF/PF identities.
    if coverage["exact_position_pct"]<40 or len(set(df.EXACT_ROLE.dropna()) & set(ROLES))<5:
        raise ValueError("Source insufficient for exact five-position DvP. Do not invent positions.")
    if coverage["DVP5_PTS_AVG_L10"]<20:
        raise ValueError("Insufficient preceding positional matchup games for L10 research.")
    df=df.sort_values(["GAME_DATE","PLAYER_ID"]).reset_index(drop=True)
    dates=np.sort(pd.to_datetime(df.GAME_DATE).unique())
    if len(dates)<130:raise ValueError("Too few calendar dates")
    first=pd.Timestamp(dates[int(len(dates)*.6)])
    second=pd.Timestamp(dates[int(len(dates)*.8)])
    tr=pd.to_datetime(df.GAME_DATE)<first
    va=(pd.to_datetime(df.GAME_DATE)>=first)&(pd.to_datetime(df.GAME_DATE)<second)
    te=pd.to_datetime(df.GAME_DATE)>=second
    if min(int(tr.sum()),int(va.sum()),int(te.sum()))<1500:
        raise ValueError("Insufficient chronological test observations")
    core=[x for x in FEATURES if x in df.columns]+list(COLS)
    variants={"team_defense":core}
    variants["exact_position_L5"]=core+["DVP5_ROLE_CODE"]+[
        f"DVP5_{s}_AVG_L5" for s in TARGETS]+["DVP5_GAMES_L5"]
    variants["exact_position_L5_L10_L20"]=core+["DVP5_ROLE_CODE"]+[
        f"DVP5_{s}_AVG_L{n}" for n in (5,10,20) for s in TARGETS]+[
        f"DVP5_GAMES_L{n}" for n in (5,10,20)]
    variants["exact_position_plus_minutes_rate"]=core+list(DETAILED_COLS)
    results=[]
    for target in TARGETS:
        row={"market":target,"test_rows":int(te.sum()),"variants":{}}
        for name,features in variants.items():
            X=df[features].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
            fill=X.loc[tr].median().fillna(0)
            X=X.fillna(fill).fillna(0)
            m=model()
            m.fit(X.loc[tr],pd.to_numeric(df.loc[tr,target]))
            pred=np.maximum(0,m.predict(X.loc[te]))
            actual=pd.to_numeric(df.loc[te,target]).to_numpy()
            row["variants"][name]={"mae":round(float(mean_absolute_error(actual,pred)),4)}
        base=row["variants"]["team_defense"]["mae"]
        for name,value in row["variants"].items():
            value["improvement_vs_team"]=round(base-value["mae"],4)
        results.append(row)
        print("DETAILED POSITION RESULT:",json.dumps(row),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    report={"generated_at":datetime.now(timezone.utc).isoformat(),
       "status":"DETAILED_DVP_RESEARCH_ONLY_NOT_DEPLOYED",
       "roles":"PG SG SF PF C (exact source listed primary role; not defender assignment)",
       "source":sources,
       "training_rows":int(tr.sum()),"validation_rows":int(va.sum()),
       "test_rows":int(te.sum()),
       "training_cutoff_exclusive":str(first.date()),"test_from":str(second.date()),
       "role_counts":{str(k):int(v) for k,v in roles.items()},
       "coverage_pct":coverage,"metrics":results,
       "limitations":["Historical source positions may be coarse or incomplete.",
                      "Per36 rates describe opposing production per logged minutes, not defensive matchups.",
                      "Models are NOT calibrated using actual sportsbook lines.",
                      "No model has been promoted to live AI."]}
    (OUT/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Detailed DvP research completed; live models unchanged",flush=True)

if __name__=="__main__":main()

"""Publish experimental next-game NBA forecasts from the trained models.

No live recommendations are generated unless current-season data is present.
Historical models are research artifacts, not sportsbook win probabilities.
"""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/nba/raw/raw_game_logs.csv"
MODELS=ROOT/"models/nba/provisional"
OUTPUT=ROOT/"docs/research_projections.json"
TARGETS=("PTS","REB","AST","PRA")

def main():
    df=pd.read_csv(RAW,low_memory=False)
    df["GAME_DATE"]=pd.to_datetime(df["GAME_DATE"],errors="raise")
    df=df.sort_values(["PLAYER_ID","GAME_DATE"])
    last_date=df["GAME_DATE"].max().date()
    now=datetime.now(timezone.utc)
    age=(now.date()-last_date).days
    recent=df[df.GAME_DATE>=df.GAME_DATE.max()-pd.Timedelta(days=70)]
    players=[]
    for _,group in recent.groupby("PLAYER_ID"):
        group=group.sort_values("GAME_DATE")
        if len(group)<5:continue
        name=str(group.PLAYER_NAME.iloc[-1]).strip()
        if not name or name=="nan":continue
        entry={"player":name,"as_of":str(group.GAME_DATE.iloc[-1].date()),
               "historical_games":int(len(group)),"forecasts":{}}
        for stat in ("PTS","REB","AST","FGA","FG3A","TOV","MIN"):
            data=pd.to_numeric(group[stat],errors="coerce").dropna()
            if len(data)<5:continue
            entry[f"{stat}_L5"]=float(data.tail(5).mean())
            entry[f"{stat}_L10"]=float(data.tail(10).mean())
            entry[f"{stat}_Season"]=float(data.ewm(span=30,adjust=False).mean().iloc[-1])
        players.append(entry)
    players=sorted(players,key=lambda p:p["player"])
    for target in TARGETS:
        item=joblib.load(MODELS/f"{target}_model.joblib")
        cols=item["features"]
        fill=item["fill_values"]
        features=pd.DataFrame([{col:p.get(col,fill.get(col,0)) for col in cols} for p in players])
        features=features.apply(pd.to_numeric,errors="coerce").fillna(pd.Series(fill)).fillna(0)
        pred=np.maximum(0,item["model"].predict(features[cols]))
        for p,v in zip(players,pred):
            p["forecasts"][target]=round(float(v),1)
    safe=[{"player":p["player"],"as_of":p["as_of"],"historical_games":p["historical_games"],
           "forecasts":p["forecasts"]} for p in players]
    result={"generated_at":now.isoformat(),"latest_game_date":str(last_date),
            "days_old":age,"current":age<=10,"historical_only":age>10,
            "model_status":"RESEARCH_ONLY","source":"Archived NBA player games; no 2026-27 live input",
            "disclaimer":"Experimental next-game forecast from archived historical data. Not live, not matchup/injury adjusted, not PrizePicks lines or calibrated betting probabilities.",
            "players":safe}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print("Wrote",len(safe),"player research forecasts. Last game",last_date,"age",age, "days",flush=True)
    if not safe:raise ValueError("No player research projections produced")

if __name__=="__main__":
    main()

"""Audit and backtest REAL timestamped sportsbook props, when matched historical lines exist.

Reads pregame observed odds or an imported CSV of the same schema. Uses matched
player + NBA-local game date, strict validation, and a chronological train /
calibration / test split. No betting edge is claimed when coverage is absent.
"""
import json
import re
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import brier_score_loss

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"data/nba/odds/observed_props.csv"
GAMES=ROOT/"data/nba/processed/training_dataset.csv"
OUT=ROOT/"models/nba/real_market"
BASE=("MIN_L5","MIN_L10","MIN_Season","DAYS_REST","IS_HOME","IS_B2B","IS_FRESH","GAMES_7D","IS_4_IN_6")
STATS=("PTS","REB","AST","FGA","FG3A","TOV")
FEATURES=BASE+tuple(f"{s}_{w}" for s in STATS for w in ("L5","L10","Season"))
TARGETS=("PTS","REB","AST","PRA")
def norm(s):
    return re.sub(r"[^a-z0-9]","",str(s).casefold())
def american_profit(odds):
    odds=float(odds)
    return odds/100 if odds>0 else 100/abs(odds)
def isodatetime(s):
    return pd.to_datetime(s,utc=True,errors="coerce")
def main():
    if not INPUT.exists():
        raise SystemExit(f"No historical sportsbook CSV at {INPUT}; first collect/import verified pregame odds.")
    quotes=pd.read_csv(INPUT,low_memory=False)
    needed={"game_date","player_name","market","bookmaker","line","over_odds","under_odds","captured_at","event_start"}
    missing=needed-set(quotes.columns)
    if missing: raise ValueError(f"Missing odds columns: {sorted(missing)}")
    original=len(quotes)
    quotes["captured_at"]=isodatetime(quotes["captured_at"])
    quotes["event_start"]=isodatetime(quotes["event_start"])
    quotes["game_date"]=pd.to_datetime(quotes["game_date"],errors="coerce").dt.normalize()
    quotes["line"]=pd.to_numeric(quotes["line"],errors="coerce")
    quotes["over_odds"]=pd.to_numeric(quotes["over_odds"],errors="coerce")
    quotes["under_odds"]=pd.to_numeric(quotes["under_odds"],errors="coerce")
    quotes=quotes.loc[
        quotes["market"].isin(TARGETS)&quotes["captured_at"].notna()&
        quotes["event_start"].notna() & (quotes["captured_at"]<quotes["event_start"])&
        quotes["game_date"].notna()&quotes["line"].notna()&
        quotes["over_odds"].notna()&quotes["under_odds"].notna()&
        ((quotes["over_odds"]<=-100)|(quotes["over_odds"]>=100))&
        ((quotes["under_odds"]<=-100)|(quotes["under_odds"]>=100))&
        ((quotes["line"]%1)==.5)
    ].copy()
    quotes["name_key"]=quotes["player_name"].map(norm)
    quotes=quotes.loc[quotes.name_key.str.len()>3]
    # One last observed pregame snapshot per sportsbook/player/stat/line/date.
    quotes=quotes.sort_values("captured_at").drop_duplicates(
        ["game_date","name_key","market","bookmaker","line"],keep="last")
    if quotes.empty:
        raise SystemExit("No valid two-sided, pregame, half-point odds records.")
    df=pd.read_csv(GAMES,low_memory=False)
    if "PLAYER_NAME" not in df.columns: raise ValueError("Training dataset has no player names")
    df["game_date"]=pd.to_datetime(df["GAME_DATE"]).dt.normalize()
    df["name_key"]=df["PLAYER_NAME"].map(norm)
    # Avoid ambiguous player-name/date matches without unique identifiers.
    duplicates=df.duplicated(["game_date","name_key"],keep=False)
    games=df.loc[~duplicates].copy()
    merged=quotes.merge(games,on=["game_date","name_key"],how="inner",validate="many_to_one")
    print(f"Input quotes {original}; valid {len(quotes)}; matched {len(merged)}",flush=True)
    if len(merged)<100:
        raise SystemExit("Insufficient matched historical pregame market lines (need >=100). "
                         "Live odds after the historical box-score archive cannot be graded until games are ingested.")
    # Split dates before any modeling; quote outcomes from same game stay together.
    all_dates=np.sort(games["game_date"].unique())
    dtrain=pd.Timestamp(all_dates[int(len(all_dates)*.6)])
    dtest=pd.Timestamp(all_dates[int(len(all_dates)*.8)])
    training=games.loc[games.game_date<dtrain]
    calibration=games.loc[(games.game_date>=dtrain)&(games.game_date<dtest)]
    test=merged.loc[merged.game_date>=dtest].copy()
    if len(test)<100: raise SystemExit("Fewer than 100 real-market quotes fall in untouched test period.")
    cols=[c for c in FEATURES if c in games.columns]
    Xtrain=training[cols].apply(pd.to_numeric,errors="coerce")
    medians=Xtrain.median().fillna(0)
    def xform(frame):
        return frame[cols].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(medians).fillna(0)
    results=[]
    for stat in TARGETS:
        tr=training.loc[pd.to_numeric(training[stat],errors="coerce").notna()]
        ca=calibration.loc[pd.to_numeric(calibration[stat],errors="coerce").notna()]
        te=test.loc[(test.market==stat)&pd.to_numeric(test[stat],errors="coerce").notna()].copy()
        if len(te)<25 or len(ca)<500: continue
        model=HistGradientBoostingRegressor(max_iter=180,max_leaf_nodes=21,max_depth=5,
           min_samples_leaf=65,learning_rate=.055,l2_regularization=4.,early_stopping=False,random_state=42)
        model.fit(xform(tr),tr[stat])
        resid=np.sort((ca[stat].to_numpy()-np.maximum(model.predict(xform(ca)),0)).astype(float))
        pred=np.maximum(model.predict(xform(te)),0)
        p_over=np.clip((len(resid)-np.searchsorted(resid,te.line.to_numpy()-pred,side="right"))/len(resid),.01,.99)
        sides=np.where(p_over>=.5,"Over","Under")
        probability=np.where(sides=="Over",p_over,1-p_over)
        # Raw sportsbook payout, no assumption of standard -110 pricing.
        prices=np.where(sides=="Over",te.over_odds.to_numpy(),te.under_odds.to_numpy())
        actual=te[stat].to_numpy()
        wins=np.where(sides=="Over",actual>te.line.to_numpy(),actual<te.line.to_numpy())
        # Integer outcomes against half-point lines cannot push.
        roi=np.mean(np.where(wins,np.array([american_profit(x) for x in prices]),-1))
        actual_over=(actual>te.line.to_numpy()).astype(int)
        result={"market":stat,"n_quotes":int(len(te)),"books":int(te.bookmaker.nunique()),
            "over_brier":round(float(brier_score_loss(actual_over,p_over)),4),
            "hit_rate_pct":round(float(wins.mean()*100),2),
            "flat_stake_roi_pct":round(float(roi*100),2),
            "selection_rule":"p >= 0.5; no EV filter",
            "note":"Retrospective pricing only; not a deployable strategy."}
        results.append(result)
        print(json.dumps(result),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    report={"status":"EXPLORATORY_REAL_BOOKMAKER_ODDS","created_at":datetime.now(timezone.utc).isoformat(),
        "train_cutoff":str(dtrain.date()),"test_cutoff":str(dtest.date()),
        "odds_source":"timestamped historical sportsbook quotes (not PrizePicks)",
        "raw_quote_count":original,"valid_quote_count":int(len(quotes)),
        "matched_quote_count":int(len(merged)),"metrics":results,
        "cautions":["Odds were matched by exact normalized name and game date; ambiguous matches excluded.",
                    "One sportsbook can quote multiple lines per game; observations are correlated.",
                    "No trading costs, delays, limits, or line movement are modeled.",
                    "Feature engineering needs an independent point-in-time audit.",
                    "No proof of profitability or forward performance."]}
    (OUT/"report.json").write_text(json.dumps(report,indent=2))
    if not results: raise SystemExit("Not enough market records per statistic to produce reliable metrics")
    print("Real-market retrospective report written",flush=True)
if __name__=="__main__":main()

"""Historical defense-versus-position features, with no same-game leakage.

2024-25/2025-26 positions are fetched from versioned third-party player game
logs. Positions are coarse G/F/C roles, not precise on-court guarding assignments.
"""
import csv,io,json,re,urllib.request
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

API="https://api.github.com/repos/xtheredshirtx/fanduel-player-data/contents/NBA/csv"
RAW="https://raw.githubusercontent.com/xtheredshirtx/fanduel-player-data/main/NBA/csv/"
SEASONS=("2024-25","2025-26")
STATS=("PTS","REB","AST","PRA")
DVP_COLS=tuple(f"DVP_{s}_L5" for s in STATS)+("DVP_SAMPLE_GAMES",)
HEAD={"User-Agent":"Sports-Bot-Positional-Research/1.0"}

def role(value):
    v=str(value or "").strip().upper().replace(" ","")
    # Source may use PG/SG/SF/PF/C, combinations or plain G/F/C.
    if v in ("PG","SG","G","G-F","F-G"):return "G"
    if v in ("SF","PF","F","F-C","C-F"):return "F"
    if v=="C":return "C"
    return None

def fetch_positions():
    req=urllib.request.Request(API,headers=HEAD)
    with urllib.request.urlopen(req,timeout=30) as r:items=json.load(r)
    all_rows=[]
    for season in SEASONS:
        pat=re.compile(r"^NBA_players_game_log_"+re.escape(season)+r"_as_of_(\d{4}-\d{2}-\d{2})\.csv$")
        versions=[(m.group(1),i["name"]) for i in items if (m:=pat.fullmatch(i.get("name","")))]
        if not versions:raise ValueError("No historical position file for "+season)
        filename=max(versions)[1]
        req=urllib.request.Request(RAW+filename,headers=HEAD)
        with urllib.request.urlopen(req,timeout=90) as resp:
            source=csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig")))
            if not {"ID","Pos","Date","Team"}.issubset(set(source.fieldnames or [])):
                raise ValueError("Historical source has no ID, Pos, Date or Team")
            for r in source:
                pos=role(r["Pos"])
                if not pos:continue
                all_rows.append({"SEASON_ID":season,"PLAYER_ID":str(r["ID"]).strip(),
                                 "POSITION_ROLE":pos,"GAME_DATE":str(r["Date"])[:10]})
        print("Loaded positional source",season,filename,flush=True)
    p=pd.DataFrame(all_rows)
    if p.empty:raise ValueError("No mapped positions")
    # Only player/season with a consistent coarse position is admitted.
    counts=p.groupby(["SEASON_ID","PLAYER_ID"])["POSITION_ROLE"].nunique()
    stable=counts[counts==1].index
    lookup=p.drop_duplicates(["SEASON_ID","PLAYER_ID"]).set_index(
        ["SEASON_ID","PLAYER_ID"]).loc[stable].reset_index()
    print("Position assignments:",len(lookup),"stable player-seasons",flush=True)
    return lookup[["SEASON_ID","PLAYER_ID","POSITION_ROLE"]]

def positional_features(raw,positions):
    needed={"SEASON_ID","PLAYER_ID","GAME_DATE","TEAM_ABBREVIATION","MATCHUP",
            "GAME_ID","PTS","REB","AST"}
    if not needed.issubset(raw):raise ValueError("Historical logs missing columns")
    df=raw.copy()
    df["PLAYER_ID"]=df["PLAYER_ID"].astype(str).str.replace(r"\.0$","",regex=True)
    df["SEASON_ID"]=df["SEASON_ID"].astype(str)
    df["GAME_DATE"]=pd.to_datetime(df["GAME_DATE"])
    df["OPPONENT"]=df["MATCHUP"].astype(str).str.rsplit(" ",n=1).str[-1]
    df=df.merge(positions,on=["SEASON_ID","PLAYER_ID"],how="left",validate="many_to_one")
    df=df[df["SEASON_ID"].isin(SEASONS)].copy()
    df["PRA"]=df["PTS"]+df["REB"]+df["AST"]
    # Opponent defensive allowance vs POSITION_ROLE is opponents' player
    # average in that role, not a mislabeled team total or DvP rank.
    grouped=df.dropna(subset=["POSITION_ROLE"]).groupby(
        ["SEASON_ID","GAME_DATE","TEAM_ABBREVIATION","OPPONENT","POSITION_ROLE"],
        as_index=False)[list(STATS)].mean()
    # Grouped values are what the offense of TEAM_ABBREVIATION did vs opponent.
    # Keep offense and defense as distinct keys. The offense's position
    # production is credited as an allowance of its OPPONENT defense.
    allowances=grouped.rename(columns={
        "TEAM_ABBREVIATION":"OFFENSE_TEAM","OPPONENT":"DEFENSE_TEAM",
        **{s:"ALLOW_"+s for s in STATS}})
    allowances=allowances.sort_values(
        ["SEASON_ID","DEFENSE_TEAM","POSITION_ROLE","GAME_DATE"])
    grouped_def=allowances.groupby(
        ["SEASON_ID","DEFENSE_TEAM","POSITION_ROLE"],sort=False)
    for s in STATS:
        allowances[f"DVP_{s}_L5"]=grouped_def["ALLOW_"+s].transform(
            lambda x:x.shift(1).rolling(5,min_periods=3).mean())
    allowances["DVP_SAMPLE_GAMES"]=grouped_def.cumcount().clip(upper=5)
    # Avoid using same-day games for pregame features.
    if allowances.duplicated(["SEASON_ID","GAME_DATE","DEFENSE_TEAM","POSITION_ROLE"]).any():
        raise ValueError("Ambiguous same-day positional defense matches")
    keys=["SEASON_ID","GAME_DATE","OPPONENT","POSITION_ROLE"]
    future=allowances.rename(columns={"DEFENSE_TEAM":"OPPONENT"})
    features=df.merge(future[keys+list(DVP_COLS)],on=keys,how="left",
                      validate="many_to_one")
    return features[["SEASON_ID","PLAYER_ID","GAME_DATE","TEAM_ABBREVIATION","POSITION_ROLE",
                     *DVP_COLS]]

def merge_training(training,features):
    left=training.copy()
    left["GAME_DATE"]=pd.to_datetime(left["GAME_DATE"])
    left["PLAYER_ID"]=left["PLAYER_ID"].astype(str).str.replace(r"\.0$","",regex=True)
    left["SEASON_ID"]=left["SEASON_ID"].astype(str)
    keys=["SEASON_ID","PLAYER_ID","GAME_DATE","TEAM_ABBREVIATION"]
    result=left.merge(features[keys+["POSITION_ROLE",*DVP_COLS]],on=keys,
                      how="left",validate="one_to_one")
    if len(result)!=len(left):raise ValueError("Positional join changed row count")
    return result

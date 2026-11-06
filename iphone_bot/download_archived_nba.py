"""Download prepackaged regular-season NBA player game logs without stats.nba.com.

Source: https://huggingface.co/datasets/Sangameshsb/nba-game-logs
Only available box-score fields are used; absent first-half data is NOT invented.
"""
from pathlib import Path
import pandas as pd
import requests
from io import BytesIO

ROOT=Path(__file__).resolve().parents[1]
SEASONS=["2022-23","2023-24","2024-25","2025-26"]
SOURCE="https://huggingface.co/datasets/Sangameshsb/nba-game-logs/resolve/main/game_logs/game_logs_{}.parquet"
STATS={"pts":"PTS","reb":"REB","ast":"AST","fgm":"FGM","fga":"FGA","fg3m":"FG3M","fg3a":"FG3A","ftm":"FTM","fta":"FTA","oreb":"OREB","dreb":"DREB","stl":"STL","blk":"BLK","tov":"TOV","plus_minus":"PLUS_MINUS"}

def main():
    from nba_api.stats.static import teams
    team_ids={t["abbreviation"]:t["id"] for t in teams.get_teams()}
    # Historical archive codes sometimes differ from official NBA abbreviations.\n    aliases={"SAN":"SAS","SA":"SAS","GS":"GSW","GOL":"GSW","PHO":"PHX","BRK":"BKN","NY":"NYK","NO":"NOP","NOR":"NOP","UTH":"UTA"}\n    frames=[]
    for season in SEASONS:
        url=SOURCE.format(season)
        print("Downloading",season,flush=True)
        response=requests.get(url,timeout=(15,120),headers={"User-Agent":"SportsBot-Research/1.0"})
        response.raise_for_status()
        raw=pd.read_parquet(BytesIO(response.content))
        required={"player_id","game_id","game_date","team","opponent","home","minutes","pts","reb","ast","fgm","fga","fg3m","fg3a","ftm","fta","oreb","dreb","stl","blk","tov"}
        missing=required-set(raw.columns)
        if missing: raise ValueError(f"{season} missing required columns: {sorted(missing)}")
        if len(raw)<15000: raise ValueError(f"{season}: unexpectedly few rows ({len(raw)})")
        df=raw.rename(columns=STATS).copy()
        df["PLAYER_ID"]=pd.to_numeric(df["player_id"],errors="raise").astype("int64")
        df["GAME_ID"]=df["game_id"].astype(str)
        df["GAME_DATE"]=pd.to_datetime(df["game_date"],errors="raise").dt.strftime("%Y-%m-%d")
        df["TEAM_ABBREVIATION"]=df["team"].astype(str).str.upper().str.strip().replace(aliases)
        df["TEAM_ID"]=df["TEAM_ABBREVIATION"].map(team_ids)
        if df["TEAM_ID"].isna().any(): raise ValueError(f"Unknown team codes: {df.loc[df.TEAM_ID.isna(),'TEAM_ABBREVIATION'].unique().tolist()}")
        df["MATCHUP"]=df["TEAM_ABBREVIATION"]+df["home"].map({True:" vs. ",False:" @ ",1:" vs. ",0:" @ "})+df["opponent"].astype(str).str.upper().str.strip().replace(aliases)
        if df["MATCHUP"].isna().any(): raise ValueError("Unrecognized home/away values")
        df["WL"]=pd.NA  # This archive does not provide verified W/L; never invent a result.\n        df["MIN"]=pd.to_numeric(df["minutes"],errors="raise")
        df["SEASON_ID"]=season
        # Original dataset has no personal fouls. Do not fabricate them.
        # The existing feature pipeline needs PF; exclude PF-dependent features
        # by using a neutral zero placeholder, with provenance flag.
        df["PF"]=0
        df["PF_DATA_AVAILABLE"]=False
        df["POSITION"]="Unknown"
        df["PLAYER_NAME"]=df.get("player_name",pd.Series("",index=df.index))
        cols=["PLAYER_ID","GAME_ID","GAME_DATE","TEAM_ID","TEAM_ABBREVIATION","MATCHUP","WL","MIN","SEASON_ID","PF","PF_DATA_AVAILABLE","PLAYER_NAME"]+list(STATS.values())
        df=df[cols]
        if df.duplicated(["PLAYER_ID","GAME_ID"]).any(): raise ValueError(f"Duplicate player/game records in {season}")
        frames.append(df)
        print(season,len(df),"rows",flush=True)
    all_logs=pd.concat(frames,ignore_index=True).sort_values(["PLAYER_ID","GAME_DATE"])
    raw_path=ROOT/"data/nba/raw/raw_game_logs.csv"
    pos_path=ROOT/"data/nba/processed/player_positions.csv"
    raw_path.parent.mkdir(parents=True,exist_ok=True)
    pos_path.parent.mkdir(parents=True,exist_ok=True)
    all_logs.to_csv(raw_path,index=False)
    all_logs[["PLAYER_ID","PLAYER_NAME","POSITION"]].drop_duplicates("PLAYER_ID").to_csv(pos_path,index=False)
    print("Saved",len(all_logs),"rows",flush=True)

if __name__=="__main__": main()

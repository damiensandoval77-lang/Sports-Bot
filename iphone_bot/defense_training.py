"""Leakage-controlled opponent defensive features from completed historical games.

Each team game's *opponent* aggregate box score is converted to allowed
team totals; opponent rolling averages use only games STRICTLY BEFORE the
prediction date. No positional defense claim is made.
"""
import numpy as np
import pandas as pd

STATS=("PTS","REB","AST","PRA")
COLS=("OPP_PTS_ALLOWED_L5","OPP_REB_ALLOWED_L5",
      "OPP_AST_ALLOWED_L5","OPP_PRA_ALLOWED_L5","OPP_DEF_SAMPLE_GAMES")

def historical_defense(raw):
    required={"GAME_ID","GAME_DATE","SEASON_ID","TEAM_ABBREVIATION",
              "MATCHUP","PTS","REB","AST"}
    if not required.issubset(raw.columns):
        raise ValueError("Missing raw game columns for opponent defense")
    df=raw.copy()
    df["GAME_DATE"]=pd.to_datetime(df["GAME_DATE"])
    df["OPPONENT"]=df["MATCHUP"].astype(str).str.rsplit(" ",n=1).str[-1]
    for stat in ("PTS","REB","AST"):
        df[stat]=pd.to_numeric(df[stat],errors="coerce")
    # Sum all player boxscores for the team within the same actual game ID.
    gamecols=["SEASON_ID","GAME_ID","GAME_DATE","TEAM_ABBREVIATION","OPPONENT"]
    team=df.groupby(gamecols,dropna=False,as_index=False)[["PTS","REB","AST"]].sum(min_count=1)
    team["PRA"]=team["PTS"]+team["REB"]+team["AST"]
    # Strictly require both sides of the same game in the source.
    opp=team.rename(columns={"TEAM_ABBREVIATION":"OPPONENT",
                             "OPPONENT":"TEAM_ABBREVIATION",
                             **{s:f"ALLOW_{s}" for s in STATS}})
    opp=opp[gamecols[:-1]+["OPPONENT"]+[f"ALLOW_{s}" for s in STATS]]
    joined=team.merge(opp,on=gamecols,how="inner",validate="one_to_one")
    # Defensive rows represent what *this team* allowed against the opponent.
    defended=joined[["SEASON_ID","GAME_ID","GAME_DATE","TEAM_ABBREVIATION"]+
                    [f"ALLOW_{s}" for s in STATS]].copy()
    defended=defended.sort_values(["SEASON_ID","TEAM_ABBREVIATION","GAME_DATE","GAME_ID"])
    grouped=defended.groupby(["SEASON_ID","TEAM_ABBREVIATION"],sort=False)
    for stat in STATS:
        defended[f"OPP_{stat}_ALLOWED_L5"]=grouped[f"ALLOW_{stat}"].transform(
            lambda x:x.shift(1).rolling(5,min_periods=3).mean())
    defended["OPP_DEF_SAMPLE_GAMES"]=grouped.cumcount().clip(upper=5)
    # For target player, map their upcoming opponent team to its prior defensive record.
    feature_cols=["SEASON_ID","GAME_ID","GAME_DATE","OPPONENT"]
    mapped=defended.rename(columns={"TEAM_ABBREVIATION":"OPPONENT"})
    result=team[gamecols].merge(mapped[feature_cols+list(COLS)],
        on=feature_cols,how="left",validate="many_to_one")
    result=result[["SEASON_ID","GAME_ID","TEAM_ABBREVIATION",*COLS]]
    # For early games rolling data is missing; model can use training-only medians.
    if result.duplicated(["SEASON_ID","GAME_ID","TEAM_ABBREVIATION"]).any():
        raise ValueError("Nonunique opponent defense mapping")
    return result


def add_historical_defense(training,raw):
    defense=historical_defense(raw)
    result=training.merge(defense,on=["SEASON_ID","GAME_ID","TEAM_ABBREVIATION"],
                          how="left",validate="many_to_one")
    if len(result)!=len(training):
        raise ValueError("Defensive feature merge changed player-game count")
    return result

"""Prior-game opponent player-level defensive box-score rotation signals.

No individual matchup or defender assignment is claimed. Pre-game team rotation
is estimated ONLY from team members seen in previous games (never the players
appearing in the target game). Uses recorded STL, BLK, DREB and MIN. PF is
unavailable in the archive and is intentionally excluded.

Each defensive fixture is represented by the last-five player performances,
weighted by *past* minutes and recent appearances. The opponent's state at
the same historical date is then merged into each offensive player row.
"""
from collections import defaultdict,deque
import numpy as np
import pandas as pd

RAW_STATS=("STL","BLK","DREB")
FEATURE_COLS=(
    "DR_STL_PER36","DR_BLK_PER36","DR_DREB_PER36",
    "DR_STL_BLK_PER36","DR_TOP3_STL_BLK_PER36",
    "DR_EST_ROTATION_MIN","DR_ROTATION_PLAYERS",
    "DR_ROTATION_HISTORY_GAMES")
KEYS=("SEASON_ID","GAME_DATE","TEAM_ABBREVIATION")
MIN_PAST_GAMES=2
MAX_INACTIVE_DAYS=21
MAX_ROTATION=9

def _normalize(raw):
    need=set(KEYS)|{"PLAYER_ID","MIN",*RAW_STATS}
    missing=need-set(raw.columns)
    if missing:raise ValueError("Missing real defender box-score fields: "+str(sorted(missing)))
    d=raw[list(need)].copy()
    d["GAME_DATE"]=pd.to_datetime(d["GAME_DATE"],errors="raise")
    d["SEASON_ID"]=d["SEASON_ID"].astype(str)
    d["TEAM_ABBREVIATION"]=d["TEAM_ABBREVIATION"].astype(str).str.strip().str.upper()
    d["PLAYER_ID"]=d["PLAYER_ID"].astype(str)
    for s in ("MIN",*RAW_STATS):
        d[s]=pd.to_numeric(d[s],errors="coerce")
    if d[["MIN",*RAW_STATS]].isna().any().any():
        raise ValueError("Historical defender boxscores have missing MIN/STL/BLK/DREB")
    if (d[["MIN",*RAW_STATS]]<0).any().any():
        raise ValueError("Historical defensive statistics cannot be negative")
    if d.duplicated([*KEYS,"PLAYER_ID"]).any():
        raise ValueError("Duplicate player-team-date in defender source")
    return d.sort_values([*KEYS,"PLAYER_ID"]).reset_index(drop=True)

def prior_rotation_features(raw):
    d=_normalize(raw)
    outputs=[]
    # State cannot leak between seasons; team membership must remain current.
    for (season,team),season_games in d.groupby(["SEASON_ID","TEAM_ABBREVIATION"],sort=False):
        state=defaultdict(lambda:deque(maxlen=5))
        for date,game in season_games.groupby("GAME_DATE",sort=True):
            candidates=[]
            for player,history in state.items():
                recent=[g for g in history if 0<(date-g[0]).days<=MAX_INACTIVE_DAYS]
                if len(recent)<MIN_PAST_GAMES:continue
                mins=np.array([g[1] for g in recent],dtype=float)
                if mins.mean()<8:continue
                denom=mins.sum()
                if denom<=0:continue
                rates={s:36*sum(g[2+i] for g in recent)/denom
                       for i,s in enumerate(RAW_STATS)}
                candidates.append({"player":player,"minutes":float(min(40,mins.mean())),
                                   "history_games":len(recent),**rates})
            candidates.sort(key=lambda x:(-x["minutes"],str(x["player"])))
            selected=candidates[:MAX_ROTATION]
            result={"SEASON_ID":season,"GAME_DATE":date,"TEAM_ABBREVIATION":team}
            if len(selected)>=5:
                weights=np.array([x["minutes"] for x in selected],dtype=float)
                total=weights.sum()
                for s in RAW_STATS:
                    result[f"DR_{s}_PER36"]=float(sum(x["minutes"]*x[s]
                                                       for x in selected)/total)
                both=[x["STL"]+x["BLK"] for x in selected]
                result["DR_STL_BLK_PER36"]=float(np.dot(weights,both)/total)
                top=selected[:3]
                result["DR_TOP3_STL_BLK_PER36"]=float(np.average(
                    [x["STL"]+x["BLK"] for x in top],
                    weights=[x["minutes"] for x in top]))
                result["DR_EST_ROTATION_MIN"]=float(total)
                result["DR_ROTATION_PLAYERS"]=len(selected)
                result["DR_ROTATION_HISTORY_GAMES"]=int(sum(x["history_games"] for x in selected))
            else:
                for col in FEATURE_COLS:result[col]=np.nan
            outputs.append(result)
            # Crucial: current game's observations are inserted only AFTER
            # this game's prediction feature snapshot has been finalized.
            for row in game.itertuples(index=False):
                if row.MIN>0:
                    state[str(row.PLAYER_ID)].append((
                        date,float(row.MIN),float(row.STL),
                        float(row.BLK),float(row.DREB)))
    result=pd.DataFrame(outputs)
    if result.empty:raise ValueError("No historical defender fixtures")
    if result.duplicated(list(KEYS)).any():
        raise ValueError("Ambiguous prior-rotation keys")
    return result[list(KEYS)+list(FEATURE_COLS)]

def attach_rotation_to_training(training,raw):
    # This is a separate, opponent-mapped feature join; no future lineup
    # availability, actual defender assignment or target-boxscore involved.
    rotation=prior_rotation_features(raw)
    keys=["SEASON_ID","GAME_DATE","OPPONENT_TEAM"]
    right=rotation.rename(columns={"TEAM_ABBREVIATION":"OPPONENT_TEAM"})
    left=training.copy()
    left["GAME_DATE"]=pd.to_datetime(left["GAME_DATE"])
    left["SEASON_ID"]=left["SEASON_ID"].astype(str)
    if "MATCHUP" not in left:raise ValueError("Training dataset missing MATCHUP for opponent mapping")
    left["OPPONENT_TEAM"]=left["MATCHUP"].astype(str).str.rsplit(" ",n=1).str[-1].str.upper()
    combined=left.merge(right,on=keys,how="left",validate="many_to_one")
    combined=combined.drop(columns=["OPPONENT_TEAM"])
    if len(combined)!=len(training):raise ValueError("Opponent defender join altered training rows")
    return combined

"""Independent-season replication of frozen defender-aware points research.

2024-25 is evaluated with the SAME fixed algorithm and hyperparameters as
2025-26, with strictly earlier in-season history. This does not train/tune on
2025-26 holdout or claim a real-time 2026-27 defender assignment.
"""
import datetime as dt
import json
from pathlib import Path

try:
    from .defender_matchup_v3 import ROOT
    from .defender_v3_points import (
        PLAYER_URL,PLAYER_FILE,load_player_games,load_defender_games,
        evaluate,retrieve)
except ImportError:
    from defender_matchup_v3 import ROOT
    from defender_v3_points import (
        PLAYER_URL,PLAYER_FILE,load_player_games,load_defender_games,
        evaluate,retrieve)

YEAR=2024
MATCHUP_URL=f"https://huggingface.co/datasets/cdechoch/nba-data-archive/resolve/main/per_season/matchups/{YEAR}.parquet"
BOXSCORE_URL=f"https://huggingface.co/datasets/Sangameshsb/nba-game-logs/resolve/main/game_logs/game_logs_{YEAR}-{str(YEAR+1)[-2:]}.parquet"
MATCHUP_FILE=ROOT/f"data/nba/research/matchups{YEAR}.parquet"
BOXSCORE_FILE=ROOT/f"data/nba/research/game_logs_{YEAR}-{str(YEAR+1)[-2:]}.parquet"
REPORT=ROOT/"docs/defender_v3_replication.json"

def run(matchup_path=MATCHUP_FILE,box_path=BOXSCORE_FILE):
    out={"status":"INDEPENDENT_SEASON_REPLICATION_UNAVAILABLE",
         "replication_season":"2024-25",
         "compared_to_development_season":"2025-26",
         "same_frozen_model_parameters":True,
         "no_holdout_tuning":True,
         "is_live_model":False,
         "validated_for_live_use":False,
         "promotion_gate":"DO_NOT_ENABLE_LIVE_MODEL"}
    try:
        import pyarrow.parquet as pq
        boxes=load_player_games(pq.read_table(box_path),season_start=YEAR)
        defenders,rejections=load_defender_games(pq.read_table(matchup_path),boxes,season_start=YEAR)
        if len(boxes)<10000 or len(defenders)<50000:
            raise ValueError("Too few independently joined game/defender observations")
        results=evaluate(boxes,defenders)
        out.update(results)
        out["status"]="INDEPENDENT_SEASON_"+results["status"]
        out["replication_season"]="2024-25"
        out["source_games"]=len(boxes)
        out["joined_defender_records"]=len(defenders)
        out["join_rejections"]=rejections
        out["independent_season_test"]=True
        out["same_frozen_model_parameters"]=True
        out["is_live_model"]=False
        out["validated_for_live_use"]=False
        out["promotion_gate"]="DO_NOT_ENABLE_LIVE_MODEL"
    except (OSError,ValueError,TypeError,KeyError,ImportError) as error:
        out["error_type"]=type(error).__name__
        out["error_detail"]=str(error)[:250]
    out["generated_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
    REPORT.write_text(json.dumps(out,indent=2)+"\n")
    return out

def main():
    try:
        retrieve(MATCHUP_FILE,MATCHUP_URL)
        retrieve(BOXSCORE_FILE,BOXSCORE_URL)
    except (OSError,ValueError,TypeError) as error:
        fallback={"status":"INDEPENDENT_SEASON_SOURCE_UNAVAILABLE",
             "replication_season":"2024-25",
             "error_type":type(error).__name__,
             "error_detail":str(error)[:250],
             "same_frozen_model_parameters":True,
             "is_live_model":False,
             "validated_for_live_use":False,
             "promotion_gate":"DO_NOT_ENABLE_LIVE_MODEL",
             "generated_at":dt.datetime.now(dt.timezone.utc).isoformat()}
        REPORT.write_text(json.dumps(fallback,indent=2)+"\n")
        print(json.dumps(fallback),flush=True)
        return
    result=run()
    print(json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":main()

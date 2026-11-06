"""Publish research-only minutes validation using completed historical player logs.

No live odds, pregame slip capture, model training or changes to forecasts.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
try:
    from .minutes_model_v2 import backtest
except ImportError:
    from minutes_model_v2 import backtest

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"data/nba/current/current_games.json"
OUTPUT=ROOT/"docs/minutes_v2_validation.json"


def main():
    games=json.loads(INPUT.read_text())
    result=backtest(games)
    result["generated_at"]=datetime.now(timezone.utc).isoformat()
    result["source"]="completed_current_season_player_games"
    result["is_research_only"]=True
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print("MINUTES V2 RESEARCH:",json.dumps({
        k:result[k] for k in ("status","eligible_samples","distinct_dates",
          "holdout_samples","baseline_mae","candidate_mae",
          "candidate_minus_baseline_mae","live_model_unchanged")
    }),flush=True)


if __name__=="__main__":main()

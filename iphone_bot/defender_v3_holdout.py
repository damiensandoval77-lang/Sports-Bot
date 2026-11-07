"""Pregame-only chronological 2025-26 defender matchup FG research.

Uses game ID order as a PROXY for chronology (not validated wall-clock game
dates); 80/20 heldout GAME IDs, so no game's matchups leak into both splits.
This evaluates shot-make probabilities, NOT points props, betting odds or
calibrated live hit percentages.
"""
import json
import math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
try:
    from .defender_matchup_v3 import ROOT,clean_matchup,SHRINK_FGA,MAX_EFFICIENCY_SHIFT
    from .import_archived_defender_matchups import normalize_schema,archive_minutes
except ImportError:
    from defender_matchup_v3 import ROOT,clean_matchup,SHRINK_FGA,MAX_EFFICIENCY_SHIFT
    from import_archived_defender_matchups import normalize_schema,archive_minutes

PARQUET=ROOT/"data/nba/research/matchups2025.parquet"
OUT=ROOT/"docs/defender_v3_holdout.json"
MIN_PAST_OFFENSE_FGA=100
MIN_PAST_PAIR_POSS=20
MIN_TEST_ATTEMPTS=1


def rows_from_parquet(table):
    columns=normalize_schema(table.column_names)
    if "game_id" not in table.column_names:
        raise ValueError("No individual historical NBA game identity")
    if "_season" not in table.column_names or "_season_type" not in table.column_names:
        raise ValueError("Historical season type unverified")
    selected=table.select(["game_id","_season","_season_type",*columns.values()])
    names=["game_id","season","season_type",*columns.keys()]
    selected=selected.rename_columns(names)
    dedup={}
    for raw in selected.to_pylist():
        if raw["season"]!=2025 or raw["season_type"]!="rg":continue
        game_id=str(raw.get("game_id") or "").strip()
        # Regular season games only; prefix 002 is required.
        if not game_id.isdigit() or not game_id.zfill(10).startswith("00225"):continue
        try:raw["MATCHUP_MIN"]=archive_minutes(raw["MATCHUP_MIN"])
        except (TypeError,ValueError):continue
        row=clean_matchup(raw)
        if row is None:continue
        key=(game_id,row["off_id"],row["def_id"])
        if key in dedup:
            # Multiple entries for same game/pair may be normal segmented data;
            # accumulate, rather than selecting a favorable observation.
            old=dedup[key]
            for field in ("poss","fga","fgm","minutes"):old[field]+=row[field]
        else:dedup[key]={"game_id":game_id,**row}
    return list(dedup.values())


def evaluate(rows):
    games=sorted({r["game_id"] for r in rows})
    result={"status":"INSUFFICIENT_HISTORICAL_GAME_HOLDOUT",
       "method":"2025-26 game-ID ordered 80/20 holdout; single season only",
       "date_limitation":"NBA game ID order is a chronology proxy; not a verified game date",
       "evaluates":"MATCHUP_SHOT_EFFICIENCY_ONLY_NOT_NBA_PLAYER_POINTS",
       "live_model_unchanged":True,"applied_to_live_ai":False,
       "minimum_prior_offensive_fga":MIN_PAST_OFFENSE_FGA,
       "minimum_prior_matchup_possessions":MIN_PAST_PAIR_POSS,
       "games_total":len(games),"training_games":0,"test_games":0,
       "eligible_test_matchups":0,"eligible_test_fga":0,
       "baseline_weighted_absolute_shot_error":None,
       "defender_weighted_absolute_shot_error":None,
       "baseline_weighted_brier":None,
       "defender_weighted_brier":None,
       "defender_brier_minus_baseline":None,
       "defender_better_on_holdout":None,
       "minimum_brier_improvement_for_promotion":0.001,
       "requires_no_absolute_shot_error_regression":True,
       "statistically_significant":False,
       "validated_for_live_use":False,
       "promotion_gate":"NOT_ELIGIBLE_INDEPENDENT_POINTS_PROP_HOLDOUT_REQUIRED"}
    if len(games)<100:return result
    split=max(1,min(len(games)-1,int(.8*len(games))))
    train_ids=set(games[:split])
    offense=defaultdict(lambda:[0.,0.])
    pair=defaultdict(lambda:[0.,0.,0.])
    for r in rows:
        if r["game_id"] not in train_ids:continue
        off=str(r["off_id"]);def_id=str(r["def_id"])
        offense[off][0]+=r["fga"];offense[off][1]+=r["fgm"]
        bucket=pair[(off,def_id)]
        bucket[0]+=r["poss"];bucket[1]+=r["fga"];bucket[2]+=r["fgm"]
    total_fga=0
    base_abs=adj_abs=base_brier=adj_brier=0.
    n=0
    for r in rows:
        if r["game_id"] in train_ids or r["fga"]<MIN_TEST_ATTEMPTS:continue
        off=str(r["off_id"]);d=str(r["def_id"])
        att,made=offense[off]
        past=pair[(off,d)]
        if att<MIN_PAST_OFFENSE_FGA or past[0]<MIN_PAST_PAIR_POSS:continue
        # Prior offensive baseline and pseudocount-smoothed specific matchup.
        baseline=(made+10)/(att+20)
        posterior=(past[2]+SHRINK_FGA*baseline)/(past[1]+SHRINK_FGA)
        adjustment=max(-MAX_EFFICIENCY_SHIFT,min(MAX_EFFICIENCY_SHIFT,
                          (posterior-baseline)/baseline))
        adjusted=max(.01,min(.99,baseline*(1+adjustment)))
        attempts=r["fga"];success=r["fgm"];missed=attempts-success
        actual=success/attempts
        base_abs+=attempts*abs(actual-baseline)
        adj_abs+=attempts*abs(actual-adjusted)
        base_brier+=success*(1-baseline)**2+missed*baseline**2
        adj_brier+=success*(1-adjusted)**2+missed*adjusted**2
        total_fga+=attempts
        n+=1
    result.update(status="HISTORICAL_DEFENDER_EFFICIENCY_HOLDOUT",
        training_games=split,test_games=len(games)-split,
        eligible_test_matchups=n,eligible_test_fga=round(total_fga,1))
    if total_fga:
        result.update(
          baseline_weighted_absolute_shot_error=round(base_abs/total_fga,5),
          defender_weighted_absolute_shot_error=round(adj_abs/total_fga,5),
          baseline_weighted_brier=round(base_brier/total_fga,6),
          defender_weighted_brier=round(adj_brier/total_fga,6),
          defender_brier_minus_baseline=round((adj_brier-base_brier)/total_fga,6),
          defender_better_on_holdout=adj_brier<base_brier,
          promotion_gate=("INSUFFICIENT_MEANINGFUL_SHOT_EFFICIENCY_GAIN" if
                          (base_brier-adj_brier)/total_fga<0.001 or
                          adj_abs>base_abs else
                          "SHOT_EFFICIENCY_RESEARCH_POSITIVE_STILL_REQUIRES_POINTS_PROP_HOLDOUT"))
    return result


def main():
    report={"generated_at":datetime.now(timezone.utc).isoformat(),
            "status":"HISTORICAL_MATCHUP_HOLDOUT_UNAVAILABLE",
            "live_model_unchanged":True,"applied_to_live_ai":False}
    try:
        if not PARQUET.exists():raise FileNotFoundError("No archived 2025-26 parquet")
        import pyarrow.parquet as pq
        rows=rows_from_parquet(pq.read_table(PARQUET))
        report.update(evaluate(rows))
        report["source"]="2025-26 independent historical NBA boxscore matchup archive"
        report["historical_rows"]=len(rows)
    except (OSError,ValueError,KeyError,TypeError,ImportError) as e:
        report.update(error_type=type(e).__name__,error_detail=str(e)[:260])
    OUT.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True),flush=True)
    return report


if __name__=="__main__":main()

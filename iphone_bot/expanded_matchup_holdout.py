"""Strict, historical 2025-26 paired matchup context research.

Compares against the identical pregame baseline and involvement-only challenger.
No fabricated official USG%, verified injuries, player positions or sportsbook odds.
No model training on 2025-26 outcomes and no live deployment.
"""
import json
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean
from math import sqrt
try:
    from .offensive_involvement_holdout import load_history_with_box_context
    from .expanded_matchup_research import build_team_games,expanded_predict
except ImportError:
    from offensive_involvement_holdout import load_history_with_box_context
    from expanded_matchup_research import build_team_games,expanded_predict

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/expanded_matchup_holdout_research.json"

def evaluate(rows):
    all_games=build_team_games(rows)
    if len(all_games)<20:raise ValueError("Reciprocal team data too sparse")
    player_games=defaultdict(list)
    for r in rows:
        if r.get("season")=="2025-26" and r.get("id") and r.get("date") and r.get("team"):
            player_games[(str(r["id"]),r["team"])].append(r)
    samples=[]
    coverage=defaultdict(int)
    for (pid,team),games in player_games.items():
        prior=[]
        by_day=defaultdict(list)
        for game in games:by_day[game["date"]].append(game)
        for day in sorted(by_day):
            target=by_day[day]
            if len(target)!=1:
                coverage["DUPLICATE_PLAYER_DATE"]+=len(target)
                continue
            game=target[0]
            result=expanded_predict(prior,day,team,game.get("opponent"),
                                    all_games,player_id=pid)
            if result["status"]=="EXPANDED_PREGAME_RESEARCH":
                coverage[result["opponent_context"]["status"]]+=1
                samples.append({"date":day,"actual":game["PTS"],
                    "baseline":result["baseline"],
                    "involvement":result["involvement_only"],
                    "expanded":result["projection"],
                    "opponent_verified":result["opponent_context"]["status"]=="PRIOR_RECIPROCAL_TEAM_BOX_CONTEXT"})
            else:coverage[result["status"]]+=1
            prior.append(game)
    if len(samples)<1000:raise ValueError("Insufficient paired player-game holdout")
    def metrics(part):
        if not part:return {"n":0}
        def err(key):
            abs_err=[abs(x[key]-x["actual"]) for x in part]
            return {"mae":round(mean(abs_err),4),
                "rmse":round(sqrt(mean((x[key]-x["actual"])**2 for x in part)),4)}
        return {"n":len(part),"distinct_dates":len({x["date"] for x in part}),
            "baseline":err("baseline"),"involvement_only":err("involvement"),
            "expanded":err("expanded"),
            "expanded_vs_baseline_mae":round(mean(abs(x["expanded"]-x["actual"])-
                                               abs(x["baseline"]-x["actual"]) for x in part),4),
            "expanded_vs_involvement_mae":round(mean(abs(x["expanded"]-x["actual"])-
                                               abs(x["involvement"]-x["actual"]) for x in part),4)}
    days=sorted({x["date"] for x in samples})
    midpoint=days[len(days)//2]
    return {"status":"HISTORICAL_EXPANDED_MATCHUP_SHADOW_HOLDOUT",
        "holdout_season":"2025-26","overall":metrics(samples),
        "first_half":metrics([x for x in samples if x["date"]<midpoint]),
        "second_half":metrics([x for x in samples if x["date"]>=midpoint]),
        "opponent_covered":metrics([x for x in samples if x["opponent_verified"]]),
        "opponent_context_coverage":sum(x["opponent_verified"] for x in samples),
        "coverage":dict(coverage),
        "feature_availability":{"offensive_involvement_proxy":True,
          "minutes_v3":True,"reciprocal_opponent_pace_efficiency":True,
          "official_usage_pct":False,
          "verified_pretip_injury_splits":False,
          "verified_coarse_position_allowances":False,
          "individual_defender_assignments":False},
        "sportsbook_quotes_included":False,"calibrated":False,
        "production_modified":False,"automatic_promotion":False,
        "limitations":["Retrospective fixed formula vs past-only box-score baselines, not live Combined AI.",
          "No sportsbook line / hit-rate / betting edge inference.",
          "Official usage, injury and position effects gated off without verified pretip labels.",
          "Fixed reference pace and points per 100 possessions are modeling assumptions.",
          "Observed prior-team defense is not on-court individual defender matchup."]}

def main():
    rows,rejections=load_history_with_box_context()
    result=evaluate(rows)
    result["source_rejections"]=rejections
    result["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print("EXPANDED_MATCHUP_HOLDOUT",json.dumps({
        "overall":result["overall"],"first_half":result["first_half"],
        "second_half":result["second_half"],
        "opponent_context_coverage":result["opponent_context_coverage"],
        "feature_availability":result["feature_availability"]}),flush=True)

if __name__=="__main__":
    main()

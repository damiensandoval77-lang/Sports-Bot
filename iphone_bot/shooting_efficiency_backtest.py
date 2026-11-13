"""Shooting V1 historical and saved-frozen Combined-AI challenger grading.

2025-26 dates are strictly chronological; each prediction sees only completed
earlier same-team games and earlier opposing team shooting observations.
Frozen Combined-AI comparison is performed on *identical* verified settled
market records only, without changing archived predictions or hit rates.
"""
import json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo
try:
    from .shot_profile_research import load_history,_weighted_mean,predict_points,TEST_SEASON
    from .shooting_efficiency_v1 import opponent_defense_index,forecast,VERSION
    from .model_performance import independent_rows,forecast_values,utc
except ImportError:
    from shot_profile_research import load_history,_weighted_mean,predict_points,TEST_SEASON
    from shooting_efficiency_v1 import opponent_defense_index,forecast,VERSION
    from model_performance import independent_rows,forecast_values,utc

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/shooting_efficiency_v1_backtest.json"

def metrics(rows):
    if not rows:return {"n":0,"games_dates":0,"baseline_mae":None,
                         "candidate_mae":None,"blended_mae":None}
    def mae(name):
        values=[abs(x[name]-x["actual"]) for x in rows if x.get(name) is not None]
        return round(mean(values),4) if values else None
    out={"n":len(rows),"games_dates":len({r["date"] for r in rows}),
       "baseline_mae":mae("baseline"),"candidate_mae":mae("candidate"),
       "blended_mae":mae("blended"),
       "opponent_adjusted":sum(r.get("opponent_adjusted") is True for r in rows)}
    eligible=[r for r in rows if r.get("line") is not None and r["actual"]!=r["line"]]
    for key in ("baseline","candidate","blended"):
        sides=[r for r in eligible if r.get(key) is not None and r[key]!=r["line"]]
        wins=sum((r[key]>r["line"])==(r["actual"]>r["line"]) for r in sides)
        out[key+"_graded"]=len(sides)
        out[key+"_wins"]=wins
        out[key+"_hit_rate"]=round(wins/len(sides),4) if sides else None
    return out

def historical(records):
    # Restrict holdout to entire 2025-26 season; no current-day outcomes.
    teams=opponent_defense_index(records)
    grouped=defaultdict(list)
    for r in records:
        grouped[(r["season"],str(r["id"]),r["team"])].append(r)
    comparisons=[]
    for (season,pid,team),games in grouped.items():
        if season!=TEST_SEASON:continue
        games.sort(key=lambda x:(x["date"],x["game_id"]))
        history=[]
        for target in games:
            day=target["date"]
            prior=[r for r in history if r["date"]<day]
            if len(prior)>=8:
                baseline=_weighted_mean([g["PTS"] for g in prior])
                old=predict_points(prior,day,team,None)
                # Predicted minutes use strictly earlier player observations.
                candidate=forecast(prior,day,team,target.get("opponent"),None,
                                   teams,season,combined_baseline=baseline)
                if old and candidate["projection"] is not None:
                    comparisons.append({
                      "date":day,"player_id":pid,"actual":target["PTS"],
                      "baseline":baseline,"candidate":candidate["projection"],
                      "blended":candidate["blended_projection"],
                      "without_opponent":candidate["unadjusted_points"],
                      "old_shot_profile":old["expected_points"],
                      "opponent_adjusted":candidate["opponent_adjustment_applied"]})
            history.append(target)
    summary=metrics(comparisons)
    if comparisons:
        summary["old_shot_profile_mae"]=round(mean(abs(x["old_shot_profile"]-x["actual"])
                                                     for x in comparisons),4)
        summary["same_minutes_no_opponent_mae"]=round(
            mean(abs(x["without_opponent"]-x["actual"]) for x in comparisons),4)
        summary["opponent_factor_mae_change"]=round(
            summary["candidate_mae"]-summary["same_minutes_no_opponent_mae"],4)
    return summary

def locked(ledger,games):
    # Strictly original frozen predictions vs NEW retrospective shadow,
    # never called prospective. Missing shooting columns => no comparison.
    index=opponent_defense_index(games)
    histories=defaultdict(list)
    for game in games:
        pid=str(game.get("id") or game.get("player_id") or "")
        if pid and game.get("team") and game.get("date"):
            histories[(pid,game["team"])].append(game)
    for group in histories.values():group.sort(key=lambda x:x["date"])
    sample=[]
    excluded=defaultdict(int)
    for r in independent_rows(ledger):
        if r.get("market")!="PTS" or r.get("status")!="SETTLED":
            continue
        try:
            date=utc(r["event_start"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
            pid=str(r["player_id"]);team=r["team"]
            prior=[g for g in histories.get((pid,team),[]) if g["date"]<date]
            original=forecast_values(r)["combined"]
            actual=float(r["actual"])
            line=float(r["line"])
            if original is None or not math.isfinite(actual):raise ValueError
            game=str(r.get("game") or "")
            # Opponent determined solely by pregame matchup identity.
            from_team=game.split(" @ ") if " @ " in game else game.split(" vs. ")
            opp=None
            if len(from_team)==2:
                # Existing archive may store full team names; do not guess.
                other=[x for x in from_team if x.strip()!=team]
                opp=other[0].strip() if len(other)==1 and len(other[0].strip())==3 else None
            prediction=forecast(prior,date,team,opp,
                None,index,None,combined_baseline=original)
            if prediction["blended_projection"] is None:
                excluded["INSUFFICIENT_PRIOR_SHOOTING"]+=1;continue
            sample.append({"date":date,"player_id":pid,"actual":actual,
                "line":line,"baseline":original,"candidate":prediction["projection"],
                "blended":prediction["blended_projection"],
                "opponent_adjusted":prediction["opponent_adjustment_applied"]})
        except (KeyError,ValueError,TypeError):
            excluded["INVALID_FROZEN_RECORD"]+=1
    return {"metrics":metrics(sample),"exclusions":dict(excluded),
            "retrospective_post_hoc":True,
            "prediction_source":"EXISTING_IMMUTABLE_COMBINED_AI_PRETIP_PROJECTIONS"}

def report(archive,ledger,games):
    return {"generated_at":datetime.now(timezone.utc).isoformat(),
       "status":"HISTORICAL_SHOOTING_SHADOW_RESEARCH_ONLY",
       "method":VERSION,"historical_holdout":historical(archive),
       "saved_combined_comparison":locked(ledger,games),
       "holdout_season":TEST_SEASON,"production_applied":False,
       "simulated_hit_rates_changed":False,"calibrated_probability":False,
       "caveats":["Historic new challenger is retrospective, not prespecified at prediction time.",
                  "Baselines are paired on identical rows; no postgame feature leakage.",
                  "Opponent factor is lagged team shot conversion, not individual defender matchup.",
                  "Injury and on/off shifts require separately verified pretip data.",
                  "Real-data improvement required before any future live promotion."]}
def main():
    archive,_=load_history()
    ledger=json.loads((ROOT/"docs/paper_pick_ledger.json").read_text()).get("records",[])
    current_file=ROOT/"data/nba/current/current_games.json"
    games=json.loads(current_file.read_text()) if current_file.exists() else []
    result=report(archive,ledger,games)
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print("SHOOTING V1:",json.dumps({k:result[k] for k in ("historical_holdout","saved_combined_comparison")}))
if __name__=="__main__":main()

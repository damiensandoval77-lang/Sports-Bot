"""Audit archived, timestamped real bookmaker quotes without fabricating outcomes.

Only previously observed two-sided PRE-GAME sportsbook odds are eligible.
Requires a completed current-season box score matched to the player, matchup,
and Eastern game date. Predictions use player games strictly before fixture.
No synthetic backfilled bookmaker lines. No claim of profitability or EV.
"""
import csv
import json
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import joblib
import numpy as np
import pandas as pd
from compare_live_models import key,matchup,predict_features,utc
from matchup_context import team_allowances

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"data/nba/odds/observed_props.csv"
FORM=ROOT/"docs/current_form.json"
GAMES=ROOT/"data/nba/current/current_games.json"
BASE=ROOT/"models/nba/provisional"
SHADOW=ROOT/"models/nba/defense_shadow"
OUT=ROOT/"docs/real_line_audit.json"

def prediction(model,features):
    names=model["features"]
    x=pd.DataFrame([{name:features.get(name,model["fill_values"].get(name,0))
                     for name in names}])[names].apply(pd.to_numeric,errors="coerce").fillna(0)
    return max(0,float(model["model"].predict(x)[0]))

def main():
    now=datetime.now(timezone.utc)
    games=json.loads(GAMES.read_text())
    form=json.loads(FORM.read_text())
    by_name=defaultdict(list)
    for person in form["players"]:
        by_name[key(person["player"])].append(person)
    history=defaultdict(list)
    for g in games:history[str(g["id"])].append(g)
    for ident in history:history[ident].sort(key=lambda x:x["date"])
    records=list(csv.DictReader(ARCHIVE.open(newline=""))) if ARCHIVE.exists() else []
    latest_completed=max((g["date"] for g in games),default=None)
    earliest_completed=min((g["date"] for g in games),default=None)
    date_counts=defaultdict(int)
    for record in records:
        date_counts[record.get("game_date","unknown")]+=1
    base_models={stat:joblib.load(BASE/f"{stat}_model.joblib") for stat in ("PTS","REB","AST","PRA")}
    shadow_models={stat:joblib.load(SHADOW/f"{stat}_model.joblib") for stat in ("PTS","REB","AST","PRA")}
    skips=defaultdict(int)
    outcomes=[]
    defensive_cache={}
    for r in records:
        try:
            captured=utc(r["captured_at"])
            start=utc(r["event_start"])
            day=start.astimezone(ZoneInfo("America/New_York")).date()
            stat=r["market"]
            line=float(r["line"])
            if stat not in base_models or not np.isfinite(line):skips["bad_market"]+=1;continue
            if captured>=start or captured>now:skips["not_pregame"]+=1;continue
            if day.isoformat()!=r["game_date"]:skips["date_mismatch"]+=1;continue
            if not r.get("over_odds") or not r.get("under_odds"):skips["incomplete_prices"]+=1;continue
        except (KeyError,TypeError,ValueError,OverflowError):
            skips["bad_quote"]+=1;continue
        # Preserve valid market quotes while their game outcomes are pending.
        # Prior-season odds require separate historical player/game matching.
        if earliest_completed and day.isoformat()<earliest_completed:
            skips["different_season_requires_historical_grading"]+=1
            continue
        if not latest_completed or day.isoformat()>latest_completed:
            skips["awaiting_completed_boxscores"]+=1
            continue
        pair=matchup(r.get("game",""))
        people=by_name[key(r["player_name"])]
        if not pair or len(people)!=1 or people[0]["team"] not in pair:
            skips["unmatched_player_or_team"]+=1;continue
        player=people[0]
        player_games=history[str(player["player_id"])]
        completed=[g for g in player_games if g["date"]==day.isoformat() and g["team"]==player["team"]]
        before=[g for g in player_games if g["date"]<day.isoformat()]
        if len(completed)!=1 or len(before)<5:
            skips["no_completed_game_or_history"]+=1;continue
        features=predict_features(before,day,player["team"]==pair[1])
        if features is None:skips["insufficient_features"]+=1;continue
        if day.isoformat() not in defensive_cache:
            defensive_cache[day.isoformat()]=team_allowances(games,day.isoformat())
        opponent=pair[0] if player["team"]==pair[1] else pair[1]
        defense=defensive_cache[day.isoformat()].get(opponent,[])
        if len(defense)<3:skips["insufficient_opponent_defense"]+=1;continue
        recent=defense[-5:]
        features.update({f"OPP_{s}_ALLOWED_L5":float(np.mean([v[s] for _,v in recent]))
                         for s in ("PTS","REB","AST","PRA")})
        features["OPP_DEF_SAMPLE_GAMES"]=min(5,len(defense))
        actual=float(completed[0][stat])
        pred_base=prediction(base_models[stat],features)
        pred_shadow=prediction(shadow_models[stat],features)
        if not np.isfinite(actual):continue
        outcomes.append({"market":stat,"player":player["player"],"game_date":str(day),
            "line":line,"actual":actual,
            "baseline_projection":round(pred_base,2),
            "shadow_projection":round(pred_shadow,2),
            "baseline_absolute_error":round(abs(pred_base-actual),3),
            "shadow_absolute_error":round(abs(pred_shadow-actual),3),
            "baseline_side_correct":None if actual==line else bool((pred_base>line)==(actual>line)),
            "shadow_side_correct":None if actual==line else bool((pred_shadow>line)==(actual>line)),
            "bookmaker":r["bookmaker"],"captured_at":r["captured_at"]})
    metrics={}
    for stat in ("PTS","REB","AST","PRA"):
        subset=[x for x in outcomes if x["market"]==stat]
        if not subset:
            metrics[stat]={"evaluated":0,"baseline_mae":None,"shadow_mae":None,
                           "baseline_direction_accuracy":None,"shadow_direction_accuracy":None}
            continue
        nonpush=[x for x in subset if x["baseline_side_correct"] is not None]
        metrics[stat]={"evaluated":len(subset),
            "baseline_mae":round(float(np.mean([x["baseline_absolute_error"] for x in subset])),3),
            "shadow_mae":round(float(np.mean([x["shadow_absolute_error"] for x in subset])),3),
            "baseline_direction_accuracy":round(float(np.mean([x["baseline_side_correct"] for x in nonpush])),3) if nonpush else None,
            "shadow_direction_accuracy":round(float(np.mean([x["shadow_side_correct"] for x in nonpush])),3) if nonpush else None}
    report={"generated_at":now.isoformat(),"status":"REAL_BOOKMAKER_QUOTES_RESEARCH_ONLY",
        "archived_quotes_seen":len(records),"verified_quote_rows":len(outcomes),
        "latest_completed_game_date":latest_completed,
        "earliest_completed_game_date":earliest_completed,
        "archived_quotes_by_game_date":dict(sorted(date_counts.items())),
        "independent_games":len({(x["player"],x["game_date"],x["market"]) for x in outcomes}),
        "skipped":dict(skips),"metrics":metrics,
        "limitations":["Quotes can repeat across books, so observed rows are correlated and not independent bets.",
                       "Recent game logs and pregame roster validation are third-party; injury/lineup status unverified.",
                       "No line-shopping, staking, commissions, real-money P/L, or PrizePicks payouts.",
                       "Models trained before the current season, and predictions use earlier game histories only.",
                       "Small real-line samples must not be interpreted as a calibrated edge."],
        "can_claim_real_line_accuracy":len({(x["player"],x["game_date"],x["market"]) for x in outcomes})>=100}
    OUT.write_text(json.dumps(report,indent=2)+"\n")
    print("Real-line audit:",len(records),"archived quotes;",len(outcomes),
          "validated rows;",report["independent_games"],"distinct player/date/market units",flush=True)
    print("Reason counts:",json.dumps(dict(skips)),flush=True)
    print("Latest completed player-game date:",latest_completed,flush=True)
    print(json.dumps(metrics),flush=True)

if __name__=="__main__":main()

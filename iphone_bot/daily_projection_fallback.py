"""Publish genuine no-line NBA player projections independent of sportsbook credits.

Research-only fallback. Uses exactly the same pretrained PTS/REB/AST/PRA
regressors as model-vs-line; NO inferred PrizePicks lines, props, odds,
confidence percentages, or wagers. Rebuilds from current verified player-game
history and independently scheduled upcoming games.
"""
import json
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import sys
# Existing trained model helper modules use local absolute imports.
sys.path.insert(0,str(Path(__file__).resolve().parent))
import joblib
import numpy as np
import pandas as pd
try:
 from .compare_live_models import predict_features,matchup
except ImportError:
 from compare_live_models import predict_features,matchup
ROOT=Path(__file__).resolve().parents[1]
FORM=ROOT/"docs/current_form.json"
GAMES=ROOT/"data/nba/current/current_games.json"
SCHEDULE=ROOT/"docs/nba_schedule.json"
OUT=ROOT/"docs/ai_projection_fallback.json"
STATS=("PTS","REB","AST","PRA")
MODEL_DIR=ROOT/"models/nba/provisional"
ET=ZoneInfo("America/New_York")
def parsed(value):
 try:
  x=datetime.fromisoformat(str(value).replace("Z","+00:00"))
  return x.astimezone(timezone.utc) if x.tzinfo else None
 except (ValueError,TypeError):return None
def build(schedule,form,games,models,now=None):
 now=now or datetime.now(timezone.utc)
 output={"generated_at":now.isoformat(),
   "status":"NO_UPCOMING_VERIFIED_SCHEDULE",
   "is_live_sportsbook_or_prizepicks":False,
   "has_actual_prop_lines":False,
   "has_calibrated_hit_percentages":False,
   "research_only":True,"predictions":[],"games_covered":0,
   "source":"TRAINED_NBA_PLAYER_REGRESSORS_WITHOUT_MARKET_LINES",
   "message":"Player-stat projections only; no wagerable line or betting direction."}
 issued=parsed(form.get("updated_at"))
 if form.get("season")!="2026-27" or not issued or (now-issued)>timedelta(hours=48) or issued>now:
  return {**output,"status":"PLAYER_HISTORY_STALE"}
 updated=parsed(schedule.get("generated_at"))
 if not updated or now-updated>timedelta(hours=18) or updated>now:
  return {**output,"status":"SCHEDULE_STALE"}
 future=[]
 for g in schedule.get("games",[]):
  if not isinstance(g,dict):continue
  tip=parsed(g.get("start"));teams=matchup(g.get("game",""))
  if not tip or not teams or not now<tip<now+timedelta(hours=42):continue
  if g.get("game_state") not in ("pre","unknown",None):continue
  future.append((g,tip,teams))
 if not future:return output
 player_groups=defaultdict(list)
 for r in games:
  if not isinstance(r,dict):continue
  pid=str(r.get("id") or "")
  if pid and r.get("date") and r.get("team"):
   player_groups[pid].append(r)
 all_players=form.get("players",[])
 for p in all_players:
  if not isinstance(p,dict):continue
  pid=str(p.get("player_id") or "")
  team=p.get("team")
  if not pid or not team:continue
  history=sorted(player_groups.get(pid,[]),key=lambda row:row["date"])
  for fixture,tip,teams in future:
   if team not in teams:continue
   local_day=tip.astimezone(ZoneInfo("America/New_York")).date()
   prior=[g for g in history if g.get("team")==team and g["date"]<local_day.isoformat()]
   if len(prior)<5:continue
   features=predict_features(prior,local_day,team==teams[1])
   if features is None:continue
   for stat in STATS:
    model=models.get(stat)
    if not isinstance(model,dict):continue
    cols=model.get("features",[])
    try:
     x=pd.DataFrame([{col:features.get(col,model.get("fill_values",{}).get(col,0))
                     for col in cols}])[cols].apply(pd.to_numeric,errors="coerce").fillna(0)
     n=float(model["model"].predict(x)[0])
     if not np.isfinite(n) or n<0:continue
     output["predictions"].append({
       "player_id":pid,"player":p.get("player"),"team":team,
       "game":fixture["game"],"start":tip.isoformat(),"stat":stat,
       "projection":round(n,1),"source_recent_games":len(prior),
       "latest_prior_game":prior[-1]["date"],
       "is_pregame_prediction":True,"line":None,"direction":None,
       "calibrated_probability":None})
    except (ValueError,TypeError,KeyError):continue
 output["games_covered"]=len({r["game"] for r in output["predictions"]})
 output["status"]="PREGAME_PROJECTIONS_NO_LINES" if output["predictions"] else "NO_ELIGIBLE_PLAYER_PROJECTIONS"
 return output
def recovered_fixture_schedule(schedule,model_input,now):
 """Use a previously authenticated NBA source as fixture evidence only.

 NO provider lines, model labels, offer prices or tiers are transferred.
 Historic evidence is kept valid for 30 hours only to avoid phantom games.
 Completeness is explicitly unknown.
 """
 existing=schedule.get("games") if isinstance(schedule,dict) else None
 updated=parsed(schedule.get("generated_at")) if isinstance(schedule,dict) else None
 if existing and updated and now-updated<timedelta(hours=18):
  if any(parsed(g.get("start")) and parsed(g["start"])>now
         and matchup(g.get("game","")) for g in existing if isinstance(g,dict)):
   return schedule
 snapshot=parsed(model_input.get("source_generated_at"))
 if (snapshot is None or snapshot>now or now-snapshot>timedelta(hours=30)
     or model_input.get("source")!="AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS"):
  return schedule
 recovered={}
 for event in model_input.get("events_covered",[]):
  if not isinstance(event,dict):continue
  tip=parsed(event.get("start"));game=event.get("game")
  if tip is None or tip<=now or tip>now+timedelta(hours=32) or not matchup(game):
   continue
  recovered[(game,tip.isoformat())]={"game":game,"start":tip.isoformat(),
           "game_state":"pre"}
 if not recovered:return schedule
 return {"generated_at":now.isoformat(),
    "status":"PARTIAL_PRIOR_AUTHENTIC_PRIZEPICKS_EVENT_TIMES",
    "source":"Verified historical PrizePicks NBA fixture identities ONLY, not current odds",
    "coverage_complete":False,
    "fixture_observed_at":snapshot.isoformat(),
    "games":list(recovered.values()),
    "total_games":len(recovered),
    "no_prop_lines_reused":True}

def retain_verified_upcoming(previous,generated,now):
 """Keep original no-line estimates for still-upcoming fixtures when a new
 run has partial coverage or a temporary upstream data failure. This does not
 reconstruct any game after tipoff or reissue stale quotes as live.
 """
 if previous.get("status")!="PREGAME_PROJECTIONS_NO_LINES":
  return generated
 old_time=parsed(previous.get("generated_at"))
 if not old_time or old_time>now or now-old_time>timedelta(hours=12):
  return generated
 if generated.get("status") not in ("PREGAME_PROJECTIONS_NO_LINES",
   "NO_ELIGIBLE_PLAYER_PROJECTIONS","SCHEDULE_STALE","PLAYER_HISTORY_STALE",
   "MODEL_OR_INPUT_UNAVAILABLE","NO_UPCOMING_VERIFIED_SCHEDULE"):
  return generated
 newest=list(generated.get("predictions",[]))
 seen={(p.get("player_id"),p.get("game"),p.get("start"),p.get("stat"))
       for p in newest}
 retained=0
 for old in previous.get("predictions",[]):
  tip=parsed(old.get("start"))
  captured=parsed(old.get("captured_at") or previous.get("generated_at"))
  if not (tip and captured and captured<tip and now<tip<now+timedelta(hours=36)):
   continue
  if old.get("is_pregame_prediction") is not True or old.get("line") is not None:
   continue
  key=(old.get("player_id"),old.get("game"),old.get("start"),old.get("stat"))
  if key in seen:continue
  seen.add(key)
  newest.append({**old,"captured_at":captured.isoformat(),
                 "retained_verified_pretip":True})
  retained+=1
 if not retained:return generated
 generated={**generated,"predictions":newest,
            "status":"PREGAME_PROJECTIONS_NO_LINES",
            "games_covered":len({p["game"] for p in newest}),
            "retained_prior_pretip_forecasts":retained,
            "last_model_refresh_status":generated.get("status"),
            "message":"Valid independent pre-tipoff estimates; some originally captured before this refresh and retained without modification."}
 return generated

def main():
 now=datetime.now(timezone.utc)
 status={"status":"UNAVAILABLE","generated_at":now.isoformat(),"predictions":[],
         "games_covered":0,"has_actual_prop_lines":False}
 try:
  models={stat:joblib.load(MODEL_DIR/f"{stat}_model.joblib") for stat in STATS}
  official=json.loads(SCHEDULE.read_text())
  archived=ROOT/"docs/prizepicks_model_input.json"
  past=json.loads(archived.read_text()) if archived.exists() else {}
  fixture_schedule=recovered_fixture_schedule(official,past,now)
  status=build(fixture_schedule,json.loads(FORM.read_text()),
               json.loads(GAMES.read_text()),models,now)
  status["fixture_source_status"]=fixture_schedule.get("status")
  status["fixture_source_complete"]=fixture_schedule.get("coverage_complete") is True
  status["fixture_last_observed_at"]=fixture_schedule.get("fixture_observed_at") or fixture_schedule.get("generated_at")
 except (OSError,ValueError,KeyError,TypeError) as e:
  status["status"]="MODEL_OR_INPUT_UNAVAILABLE"
  status["error_type"]=type(e).__name__
 previous=json.loads(OUT.read_text()) if OUT.exists() else {}
 status=retain_verified_upcoming(previous,status,now)
 OUT.write_text(json.dumps(status,separators=(",",":"))+"\n")
 print("Line-independent NBA forecast:",status["status"],
       "games:",status.get("games_covered",0),
       "stat rows:",len(status["predictions"]))
if __name__=="__main__":main()

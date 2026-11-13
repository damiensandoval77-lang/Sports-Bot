"""Assist/rebound Opportunity V2 paired to Minutes V3, strict pretip research.

Real authorized tracking is an optional separate input. Without it, AST/REB
box score rates are explicitly labeled PROXIES, never potential assists or
rebound chances. All candidate fields are frozen before game start.
"""
import math
from statistics import mean,median
try:
 from .minutes_v3_research import forecast as minutes_v3
 from .opportunity_shadow_models import forecast_opportunity
except ImportError:
 from minutes_v3_research import forecast as minutes_v3
 from opportunity_shadow_models import forecast_opportunity

VERSION="ASSIST_REBOUND_OPPORTUNITY_V2"
def num(v):
 if v is None or isinstance(v,bool):return None
 try:
  n=float(v)
  return n if math.isfinite(n) and n>=0 else None
 except (ValueError,TypeError):return None

def forecast(history,day,team,*,player_id,baseline_by_stat=None,minutes=None,
             tracking=None,team_games=None,verified_out_ids=(),
             pretip_injury_verified=False):
 baseline_by_stat=baseline_by_stat or {}
 minutes_model=minutes or minutes_v3(history,day,team,player_id=player_id,
      team_games=team_games,verified_out_ids=verified_out_ids,
      pretip_injury_verified=pretip_injury_verified)
 expected=num(minutes_model.get("expected_minutes"))
 valid=[]
 seen=set()
 for row in sorted(history,key=lambda x:str(x.get("date",""))):
  d=row.get("date")
  if not isinstance(d,str) or d>=day or row.get("team")!=team:continue
  if d in seen:continue
  seen.add(d)
  m=num(row.get("MIN"));ast=num(row.get("AST"));reb=num(row.get("REB"))
  if m is not None and 5<=m<=60 and ast is not None and reb is not None:
   valid.append((d,m,ast,reb))
 output={"model":VERSION,"expected_minutes":expected,
         "minutes_context":minutes_model,"production_applied":False,
         "tracking_data_available":bool(tracking),"markets":{}}
 for stat,ix in (("AST",2),("REB",3)):
  base=num(baseline_by_stat.get(stat))
  result={"status":"INSUFFICIENT_PRIOR_BOX_SCORE_OPPORTUNITY",
          "projection":None,"raw_projection":None,
          "market":stat,"source_kind":"BOX_SCORE_RATE_PROXY",
          "is_potential_assists":False,"is_rebound_chances":False,
          "prior_games":len(valid),"research_only":True}
  if expected is None or len(valid)<8:
   output["markets"][stat]=result;continue
  tail=valid[-10:]
  season=sum(x[ix] for x in tail)/sum(x[1] for x in tail)
  last5=median(x[ix]/x[1] for x in tail[-5:])
  raw=expected*(.65*season+.35*last5)
  source="BOX_SCORE_RATE_PROXY"
  # Tracking can replace the opportunity rate only if a real game-level
  # independent source is present and paired with earlier same-team outcomes.
  if tracking:
   mapped=forecast_opportunity(tracking,str(player_id),team,day,
        history,expected).get(stat,{})
   if mapped.get("status")=="PREGAME_OPPORTUNITY_SHADOW":
    raw=num(mapped.get("projection"))
    source="OBSERVED_TRACKING_CHANCES_CONVERTED"
  if raw is None:output["markets"][stat]=result;continue
  # The challenger must be evaluated against identical locked baseline props.
  blended=raw if base is None else max(0,base+max(-.12*max(1,base),
                                min(.12*max(1,base),.30*(raw-base))))
  output["markets"][stat]={**result,"status":"PREGAME_OPPORTUNITY_V2_RESEARCH",
    "projection":round(blended,4),"raw_projection":round(raw,4),
    "prior_games":len(tail),"last_prior_game":tail[-1][0],
    "source_kind":source,"is_potential_assists":source.startswith("OBSERVED_TRACKING"),
    "is_rebound_chances":source.startswith("OBSERVED_TRACKING"),
    "minutes_v3_used":True,"season_per36":round(season*36,4),
    "last5_median_per36":round(last5*36,4),
    "baseline":base}
 return output

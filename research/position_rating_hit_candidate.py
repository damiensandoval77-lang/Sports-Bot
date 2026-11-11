"""Simple PG/SG/SF/PF/C matchup model, RESEARCH ONLY.

Requires *sourced* per-position allowances AND an independently sourced team
defensive rating (points permitted per 100 possessions). Team-level box totals
and raw FGA+TOV activity must never masquerade as a defensive rating.
No projected individual defender, historical line-hit frequencies, or live picks.
"""
from datetime import datetime,timezone
from math import exp,isfinite
from statistics import mean

POSITIONS=("PG","SG","SF","PF","C")
MARKETS=("PTS","REB","AST","PRA")
METHOD="POSITION_V_POSITION_DEF_RATING_RESEARCH_V1"

def time(value):
    if not isinstance(value,str):raise ValueError("timestamp missing")
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone required")
    return t.astimezone(timezone.utc)

def finite(value, label, *, positive=False):
    if type(value) not in (int,float) or not isfinite(value):
        raise ValueError(label+" not finite")
    if positive and value<=0:raise ValueError(label+" not positive")
    return float(value)

def source(item,lock):
    if not isinstance(item,dict) or not isinstance(item.get("source"),str) or not item["source"].strip():
        raise ValueError("missing real source")
    if time(item.get("observed_at"))>lock:
        raise ValueError("postcapture feature")

def estimate(*,position,stat,opponent,baseline_projection,standard_line,side,
             captured_at,tipoff,position_allowed,team_def_rating,
             expected_minutes,validation_errors,model_id):
    """Separate input-source proof from predictive validation and calibration.

    Expected minutes changes the *exposure* of the existing projection.
    Position allowance / league baseline is an observational opponent-role
    signal. Defensive rating adjustment is weak and capped because rating
    and role allowances can measure overlapping defensive strength.
    These provisional coefficients MUST win a paired holdout before promotion.
    """
    lock,tip=time(captured_at),time(tipoff)
    if lock>=tip:raise ValueError("not a pregame capture")
    if position not in POSITIONS or stat not in MARKETS or not opponent or not model_id:
        raise ValueError("unknown matchup identity")
    if side not in ("MORE","LESS"):raise ValueError("invalid frozen side")
    baseline=finite(baseline_projection,"baseline",positive=True)
    line=finite(standard_line,"standard line")
    for item in (position_allowed,team_def_rating,expected_minutes):
        source(item,lock)
    if position_allowed.get("position")!=position or position_allowed.get("stat")!=stat or position_allowed.get("opponent")!=opponent:
        raise ValueError("wrong defensive positional matchup")
    sample=position_allowed.get("sample_games")
    if type(sample)!=int or sample<5:raise ValueError("insufficient opponent positional sample")
    allowed=finite(position_allowed.get("allowed_per_listed_player"),"allowed",positive=True)
    pos_league=finite(position_allowed.get("league_position_baseline"),"league role mean",positive=True)
    if team_def_rating.get("opponent")!=opponent or team_def_rating.get("metric")!="POINTS_ALLOWED_PER_100_POSSESSIONS":
        raise ValueError("opponent rating not independently verified")
    rating=finite(team_def_rating.get("rating"),"opponent defensive rating",positive=True)
    league_rating=finite(team_def_rating.get("league_baseline"),"league defensive rating",positive=True)
    minutes=finite(expected_minutes.get("matchup"),"projected minutes",positive=True)
    baseline_minutes=finite(expected_minutes.get("baseline"),"reference minutes",positive=True)
    if not 0<minutes<=48 or not 0<baseline_minutes<=48:
        raise ValueError("minutes beyond possible")
    # Damp positional context and overlapping team defense rather than double
    # multiplying both at full strength. Provisional, not learned/calibrated.
    pos_effect=max(.9,min(1.1,(allowed/pos_league)**.25))
    defense_effect=max(.96,min(1.04,(rating/league_rating)**.1))
    minute_effect=max(.6,min(1.4,minutes/baseline_minutes))
    projection=baseline*pos_effect*defense_effect*minute_effect
    if not isinstance(validation_errors,list) or len(validation_errors)<30:
        raise ValueError("missing independently validated error distribution")
    residuals=[]
    for e in validation_errors:
        if not isinstance(e,dict) or not e.get("source") or time(e.get("observed_at"))>lock:
            raise ValueError("invalid or future residual")
        if "hit_rate" in e or "line_won" in e:
            raise ValueError("historical sportsbook hit frequencies forbidden")
        residuals.append(finite(e.get("error"),"prediction error"))
    over=sum(max(0,projection+x)>line for x in residuals)/len(residuals)
    under=sum(max(0,projection+x)<line for x in residuals)/len(residuals)
    return {"method":METHOD,"model_id":model_id,"position":position,
        "opponent":opponent,"stat":stat,"captured_at":captured_at,
        "direction":side,"original_line":line,"baseline_projection":baseline,
        "matchup_projection":round(projection,3),
        "modeled_selected_probability":round(over if side=="MORE" else under,4),
        "factors":{"position_vs_position":position_allowed,
                   "team_defensive_rating":team_def_rating,
                   "projected_minutes":expected_minutes},
        "research_only":True,"calibrated":False,"production_approved":False,
        "note":"Uncalibrated prospective hypothesis; no certified matchup probability. Validate paired holdout and freeze before production."}

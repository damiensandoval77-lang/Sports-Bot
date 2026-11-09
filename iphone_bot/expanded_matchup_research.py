"""Expanded pregame context: usage proxy, minutes, opponent and positional allowance.

Research only. An observed historical absence is NOT a verified pregame OUT.
Player positions are coarse G/F/C, not on-court defensive assignments. Official
USG% cannot be inferred from individual box-score volume.
"""
import bisect
import math
from collections import defaultdict
from statistics import mean
try:
    from .minutes_v3_research import forecast as minutes_v3
    from .offensive_involvement_holdout import predict as opportunity_predict
except ImportError:
    from minutes_v3_research import forecast as minutes_v3
    from offensive_involvement_holdout import predict as opportunity_predict

REFERENCE_PACE=100.0
REFERENCE_DEF_PTS_PER_100=112.0
MIN_OPP_GAMES=5

def finite(value):
    if value is None or isinstance(value, bool):return None
    try:
        val=float(value)
        return val if math.isfinite(val) and val>=0 else None
    except (ValueError,TypeError):return None

def build_team_games(rows, season="2025-26"):
    """Reciprocal completed team boxes. A game's two sides must be present.

    Built once for speed; each query subsequently restricts date < event day.
    Full team box counts avoid partial-coverage false defensive estimates.
    """
    groups=defaultdict(list)
    for r in rows:
        if r.get("season")!=season:continue
        date,team,opp=r.get("date"),r.get("team"),r.get("opponent")
        if date and team and opp and team!=opp:
            groups[(date,team,opp)].append(r)
    result=defaultdict(list)
    seen=set()
    for key,team_rows in sorted(groups.items()):
        day,team,opp=key
        pair=(day,tuple(sorted((team,opp))))
        if pair in seen:continue
        seen.add(pair)
        opp_rows=groups.get((day,opp,team),[])
        if min(len(team_rows),len(opp_rows))<7:continue
        def totals(group):
            stat=("PTS","FGA","FTA","TOV","OREB")
            if any(finite(row.get(s)) is None for row in group for s in stat):
                return None
            value={s:sum(float(row[s]) for row in group) for s in stat}
            possessions=value["FGA"]+.44*value["FTA"]-value["OREB"]+value["TOV"]
            if not 60<=possessions<=130:return None
            value["poss"]=possessions
            return value
        a,b=totals(team_rows),totals(opp_rows)
        if a is None or b is None:continue
        result[team].append((day,a,b))
        result[opp].append((day,b,a))
    return {t:sorted(v,key=lambda x:x[0]) for t,v in result.items()}

def _prior(team_games,team,day,window=5):
    games=team_games.get(team,[])
    dates=[g[0] for g in games]
    stop=bisect.bisect_left(dates,day)
    return games[max(0,stop-window):stop]

def defense_factor(team_games,team,opponent,day):
    """Only pregame reciprocal completed boxes, not individual defender effects."""
    own=_prior(team_games,team,day)
    opp=_prior(team_games,opponent,day)
    out={"status":"NO_VERIFIED_PREGAME_DEFENSIVE_SAMPLE",
         "factor":1.0,"pace_factor":None,"defense_factor":None,
         "opponent_games":len(opp),"individual_defender_inferred":False}
    if min(len(own),len(opp))<MIN_OPP_GAMES:return out
    own_pace=mean(x[1]["poss"] for x in own)
    opp_pace=mean(x[1]["poss"] for x in opp)
    opp_points_allowed=mean(100*x[2]["PTS"]/x[2]["poss"] for x in opp)
    pace=max(.94,min(1.06,math.sqrt(own_pace*opp_pace)/REFERENCE_PACE))
    defense=max(.94,min(1.06,opp_points_allowed/REFERENCE_DEF_PTS_PER_100))
    factor=max(.94,min(1.06,1+.20*(pace*defense-1)))
    return {**out,"status":"PRIOR_RECIPROCAL_TEAM_BOX_CONTEXT",
            "factor":round(factor,5),"pace_factor":round(pace,5),
            "defense_factor":round(defense,5),"opponent_games":len(opp),
            "reference_pace":REFERENCE_PACE,
            "reference_defense_points_per_100":REFERENCE_DEF_PTS_PER_100}

def position_context(dvp_index,opponent,day,role):
    """Consume only verified prior observed coarse-role allowances.

    Rows must be (date, opponent, role, allowed_pts, role_samples).
    No complete defender assignment can be claimed from this input.
    """
    if role not in ("G","F","C") or dvp_index is None:
        return {"status":"POSITION_DATA_UNAVAILABLE","factor":1.0}
    prior=[x for x in dvp_index.get((opponent,role),[]) if x[0]<day and x[2]>=2][-5:]
    if len(prior)<3:return {"status":"INSUFFICIENT_PRIOR_POSITION_SAMPLE","factor":1.0}
    # Descriptive league-style comparison to constant reference, very conservative.
    # Do not apply when matching positional league reference is unavailable.
    return {"status":"POSITION_DESCRIPTIVE_ONLY_NOT_APPLIED","factor":1.0,
            "prior_games":len(prior)}

def expanded_predict(history,day,team,opponent,team_games,*,player_id=None,
                     verified_out_ids=(),pretip_injury_verified=False,
                     role=None,dvp_index=None,official_usage_pct=None,
                     usage_source_verified=False):
    """Combine components once; no repeated opponent multiplier.

    A verified official USG% can be represented as context, not blindly
    multiplied into a model trained without that covariate.
    """
    base=opportunity_predict(history)
    if base is None:return {"status":"INSUFFICIENT_PRIOR_HISTORY",
                            "projection":None,"research_only":True}
    minute=minutes_v3(history,day,team,player_id=player_id,
                      verified_out_ids=verified_out_ids,
                      pretip_injury_verified=pretip_injury_verified)
    minutes=finite(minute.get("expected_minutes"))
    old_minutes=base["minutes_projection"]
    if minutes is None or old_minutes<=0:
        minutes=old_minutes
    minutes_ratio=max(.92,min(1.08,minutes/old_minutes))
    defense=defense_factor(team_games,team,opponent,day)
    positional=position_context(dvp_index,opponent,day,role)
    # One opponent-wide adjustment max. Position effect is descriptive until
    # stable player position and league positional reference are validated.
    shift=base["challenger"]*minutes_ratio*defense["factor"]
    # Cap expanded shift relative to simple original recent-form baseline.
    anchor=base["baseline"]
    delta=max(-.15*max(1,anchor),min(.15*max(1,anchor),shift-anchor))
    projected=max(0.,anchor+delta)
    usage=finite(official_usage_pct) if usage_source_verified else None
    if usage is not None and usage>100:usage=None
    return {"status":"EXPANDED_PREGAME_RESEARCH",
        "baseline":round(anchor,4),"projection":round(projected,4),
        "involvement_only":round(base["challenger"],4),
        "involvement_proxy":round(base["involvement_proxy"],5),
        "official_usage_pct":usage,
        "official_usage_applied":False,
        "minutes_v3":minutes,"minutes_ratio":round(minutes_ratio,5),
        "verified_teammate_absence_applied":bool(minute.get("verified_out_context_applied")),
        "opponent_context":defense,"position_context":positional,
        "opponent_adjustment_count":1 if defense["factor"]!=1 else 0,
        "injury_unverified_not_inferred":not pretip_injury_verified,
        "research_only":True,"production_modified":False,"calibrated":False}

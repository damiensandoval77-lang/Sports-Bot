"""Conservative pregame projection updates for verified NBA game-day absences.

Sources must be official OUT statuses already matched by player ID, team and
game date. Only earlier completed game logs are used. If no supported sample
exists, do not publish an unchanged prediction as injury-adjusted. Never
retroactively modify an earlier captured forecast.
"""
import math
from statistics import mean

def finite(x):
    if isinstance(x,bool) or x is None:return None
    try:
        n=float(x)
        return n if math.isfinite(n) and n>=0 else None
    except (TypeError,ValueError,OverflowError):
        return None

def teammate_minutes_ratio(scenario,number_out):
    """Fixed bounded minutes response requiring independently observed splits."""
    if number_out==0:return 1.0
    if number_out!=1 or not isinstance(scenario,dict):return None
    if scenario.get("status")!="HISTORICAL_SCENARIO_RESEARCH_ONLY":return None
    if min(scenario.get("with_games",0),scenario.get("without_games",0))<3:return None
    base=finite(scenario.get("baseline_minutes"))
    new=finite(scenario.get("scenario_minutes"))
    if base is None or base<=0 or new is None:return None
    return max(.90,min(1.10,new/base))

def opponent_defense_ratio(allowed,opponent,player_ids,completed_games,as_of,market):
    """Observed team defense with/without absent opponent, strictly past games.

    A missing athlete is treated as absent only in a fully covered reciprocal
    box score in team_allowances, not an incomplete daily roster.
    """
    if not player_ids:return 1.0
    prior=[(date,values) for date,values in allowed.get(opponent,[])
           if date<as_of and market in values]
    if not prior:return None
    total=1.
    for pid in player_ids:
        played={str(g.get("date")) for g in completed_games
                if str(g.get("id"))==str(pid) and g.get("team")==opponent
                and str(g.get("date",""))<as_of and (finite(g.get("MIN")) or 0)>0}
        with_player=[v[market] for date,v in prior if date in played]
        without_player=[v[market] for date,v in prior if date not in played]
        if min(len(with_player),len(without_player))<3:return None
        with_avg=mean(with_player[-8:])
        without_avg=mean(without_player[-8:])
        if with_avg<=0:return None
        # Shrink historical team results toward no effect; not causal proof.
        relative=max(.93,min(1.07,(without_avg/with_avg)**.5))
        total*=relative
    return max(.88,min(1.12,total))

def reproject(original,opponent_aware,teammate_ratio,opponent_ratio):
    """Update both model outputs consistently, never the pre-injury archive."""
    x=finite(original)
    y=finite(opponent_aware)
    if x is None or teammate_ratio is None or opponent_ratio is None:
        return None
    if not all(math.isfinite(v) and v>0 for v in (teammate_ratio,opponent_ratio)):
        return None
    factor=max(.85,min(1.15,teammate_ratio*opponent_ratio))
    primary=round(x*factor,4)
    defense=round(y*factor,4) if y is not None else None
    combined=(primary+defense)/2 if defense is not None else primary
    return {"original":primary,"opponent":defense,
            "combined":round(combined,4),"factor":round(factor,5),
            "method":"VERIFIED_OUT_PAST_ONLY_BOUNDED_OPPORTUNITY_AND_DEFENSE"}

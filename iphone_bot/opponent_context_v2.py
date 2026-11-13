"""Opponent-aware V2, research only. Strictly prior reciprocal game logs.

Estimates possessions using FGA + .44*FTA - OREB + TOV when recorded;
otherwise uses defensive team totals. Never infers an individual defender
assignment or causal effect from an OUT designation.
"""
from collections import defaultdict
from statistics import mean
import math
MARKETS=("PTS","REB","AST","PRA")
STATS=("PTS","REB","AST","FGA","FTA","OREB","TOV")
def val(x):
    if x is None or isinstance(x,bool):return None
    try:
        v=float(x)
        return v if math.isfinite(v) and v>=0 else None
    except (TypeError,ValueError,OverflowError):return None

def games_by_team(games,day):
    pairs=defaultdict(list)
    for r in games:
        d=str(r.get("date",""));a=r.get("team");b=r.get("opponent")
        if d and d<day and a and b and a!=b:pairs[(d,a,b)].append(r)
    result=defaultdict(list);seen=set()
    def totals(rows):
        data={}
        for stat in STATS:
            nums=[val(r.get(stat)) for r in rows]
            data[stat]=sum(nums) if all(n is not None for n in nums) else None
        if any(data[k] is None for k in MARKETS[:3]):return None
        data["PRA"]=sum(data[k] for k in MARKETS[:3])
        if all(data[k] is not None for k in ("FGA","FTA","OREB","TOV")):
            n=data["FGA"]+.44*data["FTA"]-data["OREB"]+data["TOV"]
            data["poss"]=n if 60<=n<=125 else None
        else:data["poss"]=None
        return data
    for (d,a,b),rows in sorted(pairs.items()):
        other=pairs.get((d,b,a),[])
        k=(d,tuple(sorted((a,b))))
        if k in seen or len(rows)<7 or len(other)<7:continue
        seen.add(k);x=totals(rows);y=totals(other)
        if x is None or y is None:continue
        result[a].append((d,x,y));result[b].append((d,y,x))
    for team in result:result[team].sort(key=lambda r:r[0])
    return result

def matchup(teams,team,opponent,market,out_ids=()):
    result={"status":"INSUFFICIENT_OPPONENT_GAMES","relative_factor":None,
      "pace_ratio":None,"defensive_efficiency_ratio":None,
      "out_defender_ids":sorted(set(str(x) for x in out_ids)),
      "individual_defender_impact_applied":False,"research_only":True}
    if market not in MARKETS:return dict(result,status="UNSUPPORTED_STAT")
    attack=teams.get(team,[])[-5:];defend=teams.get(opponent,[])[-5:]
    league=[r for group in teams.values() for r in group]
    if min(len(attack),len(defend))<3 or len(league)<30:return result
    league_allowed=mean(r[2][market] for r in league)
    if league_allowed<=0:return result
    ratio=mean(r[2][market] for r in defend)/league_allowed
    samples=attack+defend
    pace=None;efficiency=None
    if all(r[1]["poss"] is not None and r[2]["poss"] is not None for r in league):
        league_pos=mean(r[1]["poss"] for r in league)
        attack_pos=mean(r[1]["poss"] for r in attack)
        defend_pos=mean(r[1]["poss"] for r in defend)
        league_eff=mean(100*r[2][market]/r[2]["poss"] for r in league)
        opp_eff=mean(100*r[2][market]/r[2]["poss"] for r in defend)
        if league_pos>0 and league_eff>0:
            pace=math.sqrt(attack_pos*defend_pos)/league_pos
            efficiency=opp_eff/league_eff
    raw=pace*efficiency if pace is not None else ratio
    factor=max(.92,min(1.08,1+.25*(raw-1)))
    return {**result,"status":"PACE_EFFICIENCY_PAST_ONLY" if pace is not None else "DEFENSIVE_TOTALS_PAST_ONLY",
      "relative_factor":round(factor,5),"pace_ratio":round(pace,5) if pace is not None else None,
      "defensive_efficiency_ratio":round(efficiency,5) if efficiency is not None else None,
      "recent_opponent_games":len(defend),"defense_allowed_ratio":round(ratio,5)}

def shadow(baseline,record):
    p=val(baseline);factor=record.get("relative_factor")
    return round(p*factor,4) if p is not None and factor is not None else None

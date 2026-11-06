"""Pregame, descriptive opponent and minutes context for Sports-Bot.

Only completed player-games BEFORE the upcoming matchup are eligible.
Defensive allowances are full-team opponent totals, not individual position
matchups, expected value, or trained-model adjustment factors.
"""
from collections import defaultdict
from datetime import date
from statistics import mean, pstdev

STATS=("PTS","REB","AST")

def team_allowances(games,as_of):
    """Opponents' recorded player totals by team/date, with reciprocal opponent check."""
    by_match=defaultdict(list)
    for g in games:
        if g.get("date","")>=as_of or not g.get("team") or not g.get("opponent"):continue
        if any(g.get(k) is None for k in STATS):continue
        by_match[(g["date"],g["team"],g["opponent"])].append(g)
    allowed=defaultdict(list)
    seen=set()
    for (day,team,opponent),first in by_match.items():
        second=by_match.get((day,opponent,team),[])
        gid=(day,tuple(sorted((team,opponent))))
        if gid in seen or len(first)<7 or len(second)<7:continue
        seen.add(gid)
        allowed[team].append((day,{k:sum(float(r[k]) for r in second) for k in STATS}))
        allowed[opponent].append((day,{k:sum(float(r[k]) for r in first) for k in STATS}))
    for team in allowed:
        allowed[team].sort(key=lambda x:x[0])
    return allowed

def defense_context(allowed,opponent,stat):
    """Return recent points/rebounds/assists allowed compared with league average."""
    items=allowed.get(opponent,[])
    if len(items)<3 or stat not in STATS:return None
    latest=[v[stat] for _,v in items[-5:]]
    league=[v[stat] for rows in allowed.values() for _,v in rows]
    if len(league)<30:return None
    baseline=mean(league)
    if baseline<=0:return None
    ratio=mean(latest)/baseline
    return {"opponent":opponent,"games":len(latest),
            "allowed_l5":round(mean(latest),1),"league_avg":round(baseline,1),
            "vs_league_pct":round((ratio-1)*100,1),
            "label":"More conceded" if ratio>=1.05 else "Fewer conceded" if ratio<=.95 else "Near average",
            "type":"DESCRIPTIVE_TEAM_TOTALS_NOT_POSITIONAL"}

def minutes_context(games):
    """Observed minutes only; never assert a future or confirmed rotation."""
    mins=[float(g["MIN"]) for g in games if g.get("MIN") is not None]
    if len(mins)<5:return None
    recent=mins[-5:]
    avg=mean(recent)
    s=pstdev(recent)
    last3=mean(mins[-3:])
    return {"observed_l5":round(avg,1),"observed_l3":round(last3,1),
            "volatility_l5":round(s,1),"review_needed":s>7 or abs(last3-avg)>5,
            "projected_minutes":None,"confirmed_injury_status":None}

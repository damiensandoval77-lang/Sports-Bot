"""Strict pregame research inputs: positional defense, observed minutes and teammate overlap.
Never treat position groups as actual defensive assignments or historical minutes as confirmed future minutes.
"""
from collections import defaultdict
from statistics import mean,pstdev

POS={"PG":"G","SG":"G","G":"G","SF":"F","PF":"F","F":"F","C":"C","CENTER":"C"}
STATS=("PTS","REB","AST","PRA")

def position_group(position):
    return POS.get(str(position or "").strip().upper())

def minutes_estimate(history,as_of):
    rows=[r for r in history if r.get("date","")<as_of and isinstance(r.get("MIN"),(int,float)) and 0<r["MIN"]<=60]
    if len(rows)<5:return {"status":"INSUFFICIENT_RECENT_MINUTES","expected_minutes":None,"games":len(rows),"is_confirmed":False}
    rows=sorted(rows,key=lambda x:x["date"])
    last5=[r["MIN"] for r in rows[-5:]]
    # descriptive research-only recent average; no promises about tomorrow's rotation
    candidate=round(.65*mean(last5[-3:])+.35*mean(last5),1)
    return {"status":"RESEARCH_ESTIMATE_UNVERIFIED_LINEUP","expected_minutes":candidate,
            "observed_l5":round(mean(last5),1),"l5_volatility":round(pstdev(last5),1),
            "games":len(rows),"is_confirmed":False,
            "requires_review":pstdev(last5)>6 or abs(mean(last5[-3:])-mean(last5))>5}

def positional_allowance(games,as_of,opponent,position,stat):
    group=position_group(position)
    if not group or stat not in STATS:return None
    # Per opposing team/game, sum observed production of EVERY opponent player
    # in that same broad position group, not what a specific defender allowed.
    rows=defaultdict(list)
    for r in games:
        if r.get("date","")>=as_of or r.get("opponent") is None:continue
        if position_group(r.get("position"))!=group:continue
        if not isinstance(r.get(stat),(float,int)) or r[stat]<0:continue
        rows[(r["date"],r["opponent"])].append(r)
    grouped=defaultdict(list)
    for (day,defense),players in rows.items():
        # Require multiple position group players; single-player totals are biased.
        if len(players)<2:continue
        grouped[defense].append((day,sum(float(p[stat]) for p in players)))
    recent=sorted(grouped.get(opponent,[]))[-5:]
    league=[v for arr in grouped.values() for _,v in arr]
    if len(recent)<3 or len(league)<30:return None
    baseline=mean(league)
    if baseline<=0:return None
    allowed=mean(v for _,v in recent)
    return {"status":"DESCRIPTIVE_POSITION_GROUP_NOT_INDIVIDUAL_MATCHUP",
            "position_group":group,"opponent":opponent,"market":stat,
            "games":len(recent),"allowed_l5":round(allowed,1),
            "league_group_avg":round(baseline,1),
            "vs_league_pct":round((allowed/baseline-1)*100,1),
            "included_player_games_before":as_of}

def teammate_on_off(history,all_team_games,as_of,teammate_id,stat):
    """Observed teammate with/without split; deliberately no hypothetical injury effect."""
    if stat not in STATS:return None
    teammate={str(g["date"]) for g in all_team_games
              if str(g.get("id"))==str(teammate_id) and g.get("date","")<as_of and
              isinstance(g.get("MIN"),(int,float)) and g["MIN"]>=1}
    samples={"with":[],"without":[]}
    for g in history:
        if g.get("date","")>=as_of or not isinstance(g.get(stat),(int,float)):continue
        bucket="with" if g["date"] in teammate else "without"
        samples[bucket].append(g[stat])
    if len(samples["with"])<3 or len(samples["without"])<3:return None
    return {"status":"OBSERVED_SPLIT_NOT_CAUSAL",
            "with_games":len(samples["with"]),"without_games":len(samples["without"]),
            "with_avg":round(mean(samples["with"]),1),
            "without_avg":round(mean(samples["without"]),1)}

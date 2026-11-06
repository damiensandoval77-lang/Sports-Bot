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

def teammate_minutes_sensitivity(history,all_games,as_of,player_team,teammate_id,
                                 min_each=3,max_abs_delta=5.0):
    """Research-only minutes difference for verified-absent teammate.

    Uses only past dates, exact teammate ID, and the target player's same-team
    games. An absent teammate is inferred only when OTHER roster teammates
    establish the team played; source coverage still cannot establish cause.
    Historical splits are observational, not causal injury effects.
    """
    teammate_id=str(teammate_id)
    played={str(g.get("date")) for g in all_games
            if str(g.get("id"))==teammate_id
            and g.get("team")==player_team
            and str(g.get("date",""))<as_of
            and isinstance(g.get("MIN"),(int,float)) and g["MIN"]>=1}
    # Team player-game records show that the team played on this date.
    # Require multiple player logs per date to avoid a partial-feed false absence.
    coverage=defaultdict(set)
    for g in all_games:
        day=str(g.get("date",""))
        if day>=as_of or g.get("team")!=player_team:continue
        if isinstance(g.get("MIN"),(int,float)) and g["MIN"]>=1:
            coverage[day].add(str(g.get("id")))
    samples={"with":[],"without":[]}
    for g in history:
        day=str(g.get("date",""))
        minutes=g.get("MIN")
        if day>=as_of or g.get("team")!=player_team or len(coverage[day])<5:
            continue
        if not isinstance(minutes,(int,float)) or not 0<minutes<=60:
            continue
        group="with" if day in played else "without"
        samples[group].append(float(minutes))
    if min(len(samples["with"]),len(samples["without"]))<min_each:
        return {"status":"INSUFFICIENT_TEAMMATE_MINUTES_SAMPLE",
                "with_games":len(samples["with"]),
                "without_games":len(samples["without"]),
                "minutes_delta":None}
    # Restrict to recent past observations to avoid mixing distant rotations.
    delta=mean(samples["without"][-10:])-mean(samples["with"][-10:])
    return {"status":"HISTORICAL_MINUTES_SPLIT_NON_CAUSAL",
            "with_games":len(samples["with"]),
            "without_games":len(samples["without"]),
            "with_avg":round(mean(samples["with"][-10:]),2),
            "without_avg":round(mean(samples["without"][-10:]),2),
            "minutes_delta":round(max(-max_abs_delta,min(max_abs_delta,delta)),2),
            "raw_minutes_delta":round(delta,2),
            "causal_effect_verified":False}


def injury_minutes_research(history,all_games,as_of,team,verified_out_teammates):
    """Estimate a cautious hypothetical rotation scenario, NEVER a live adjustment.

    Requires 5 past games and at least 3 with/without teammate games. Only
    one teammate can drive the scenario so multiple outages aren't summed.
    """
    baseline=minutes_estimate(history,as_of)
    result={"status":"NO_ELIGIBLE_VERIFIED_TEAMMATE_OUT",
            "baseline_minutes":baseline.get("expected_minutes"),
            "scenario_minutes":None,"teammate":None,
            "delta_minutes":None,"live_adjustment_applied":False,
            "is_confirmed":False,"limitation":"Non-causal historical research; not a verified rotation."}
    if baseline.get("expected_minutes") is None:return dict(result,status="INSUFFICIENT_RECENT_MINUTES")
    candidates=[]
    for p in verified_out_teammates:
        split=teammate_minutes_sensitivity(
            history,all_games,as_of,team,p["player_id"])
        if split["minutes_delta"] is None:continue
        candidates.append((split["with_games"]+split["without_games"],
                           str(p["player_id"]),p,split))
    if not candidates:
        return dict(result,status="INSUFFICIENT_TEAMMATE_SPLITS" if verified_out_teammates
                    else result["status"])
    _,__,p,split=sorted(candidates,key=lambda x:(-x[0],x[1]))[0]
    scenario=round(max(0,min(48,baseline["expected_minutes"]+split["minutes_delta"])),1)
    return {**result,"status":"HISTORICAL_SCENARIO_RESEARCH_ONLY",
            "scenario_minutes":scenario,"delta_minutes":split["minutes_delta"],
            "teammate":p["player"],"teammate_id":str(p["player_id"]),
            "with_games":split["with_games"],"without_games":split["without_games"],
            "historical_with_avg":split["with_avg"],
            "historical_without_avg":split["without_avg"]}


def minutes_walkforward_backtest(all_games,minimum_test=20):
    """Evaluate baseline on later held-out games; no injury facts are backfilled.

    This benchmark compares forecasts formed strictly before tipoff. It does
    not validate injury-specific adjustments, which need stored pregame injury
    snapshots and observed minutes for subsequent games.
    """
    by_player=defaultdict(list)
    for g in all_games:
        if g.get("id") is not None and g.get("date") and isinstance(g.get("MIN"),(int,float)):
            by_player[str(g["id"])].append(g)
    samples=[]
    for games in by_player.values():
        games=sorted(games,key=lambda x:x["date"])
        for i in range(5,len(games)):
            observed=games[i]
            if not 0<float(observed["MIN"])<=60:continue
            pred=minutes_estimate(games[:i],observed["date"])["expected_minutes"]
            if pred is not None:samples.append((observed["date"],pred,float(observed["MIN"])))
    samples.sort()
    if len(samples)<minimum_test:
        return {"status":"INSUFFICIENT_HOLDOUT_MINUTES",
                "evaluated":len(samples),"baseline_mae":None,
                "injury_scenario_mae":None,"live_model_unchanged":True}
    # Report a chronological last-quarter holdout, not fitted historical accuracy.
    test=samples[-max(minimum_test,len(samples)//4):]
    mae=sum(abs(pred-actual) for _,pred,actual in test)/len(test)
    return {"status":"PREGAME_BASELINE_HOLDOUT_ONLY",
            "evaluated":len(test),"baseline_mae":round(mae,3),
            "injury_scenario_mae":None,"live_model_unchanged":True,
            "notice":"An injury-specific holdout needs pregame-locked injury statuses; never infer old injuries from today's report."}

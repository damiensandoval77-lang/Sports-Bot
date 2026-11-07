"""Fixed early-season minutes candidate with chronological scoring.

Research only. The live player-stat model and reported injury status are
unmodified. Only completed prior games from the same player TEAM are used.
"""
from collections import defaultdict
from datetime import date
from statistics import mean,median,pstdev
from .minutes_model_v2 import numeric_minutes,player_history

METHOD="EARLY_SEASON_ROBUST_MINUTES_V3_RESEARCH_ONLY"
MIN_HISTORY=5

def forecast(history,as_of,team):
    rows=player_history(history,as_of,team)
    result={"method":METHOD,"status":"INSUFFICIENT_SAME_TEAM_HISTORY",
            "expected_minutes":None,"history_games":len(rows),
            "volatility_last5":None,"season_minutes_average":None,
            "history_confidence":"UNAVAILABLE","production_applied":False,
            "last_observed_date":rows[-1][0] if rows else None}
    if len(rows)<MIN_HISTORY:return result
    values=[v for _,v in rows]
    last5=values[-5:];last3=values[-3:]
    season=values[-20:]
    variance=pstdev(last5)
    raw=.50*mean(last3)+.25*mean(last5)+.25*mean(season)
    shrink=min(.45,max(0.,(variance-5.)/24.))
    estimated=(1.-shrink)*raw+shrink*median(last5)
    result.update(status="RESEARCH_FORECAST_UNVALIDATED",
                  expected_minutes=round(max(0,min(48,estimated)),2),
                  history_confidence=("LIMITED_5_TO_7_GAMES" if len(rows)<8
                      else "VOLATILE_REQUIRES_REVIEW" if variance>6
                      else "HISTORICAL_NOT_LINEUP_VERIFIED"),
                  volatility_last5=round(variance,2),
                  season_minutes_average=round(mean(season),2),
                  observed_last5=round(mean(last5),2),
                  observed_last3=round(mean(last3),2),
                  requires_lineup_review=True)
    return result

def backtest(all_games,minimum_test=20,minimum_dates=3):
    """Evaluate baseline and candidate on same later games, by full date."""
    try:
        from .research_context import minutes_estimate
    except ImportError:
        from research_context import minutes_estimate
    games=defaultdict(list)
    for g in all_games:
        day=str(g.get("date",""))
        if g.get("id") is None or not g.get("team"):continue
        try:date.fromisoformat(day)
        except ValueError:continue
        if numeric_minutes(g.get("MIN")) is None:continue
        games[(str(g["id"]),g["team"])].append(g)
    observations=[]
    for (pid,team),group in games.items():
        dedup={}
        conflicts=set()
        for g in group:
            day=g["date"]
            m=numeric_minutes(g["MIN"])
            if day in dedup and numeric_minutes(dedup[day]["MIN"])!=m:conflicts.add(day)
            dedup[day]=g
        for day in conflicts:dedup.pop(day,None)
        ordered=[dedup[day] for day in sorted(dedup)]
        for g in ordered:
            day=g["date"]
            prior=[x for x in ordered if x["date"]<day]
            b=minutes_estimate(prior,day).get("expected_minutes")
            c=forecast(prior,day,team)["expected_minutes"]
            if b is None or c is None:continue
            observations.append((day,pid,team,float(g["MIN"]),float(b),float(c)))
    observations.sort()
    days=sorted({x[0] for x in observations})
    result={"method":METHOD,"status":"INSUFFICIENT_CHRONOLOGICAL_SAMPLES",
            "eligible_player_games":len(observations),"distinct_dates":len(days),
            "earlier_samples":0,"holdout_samples":0,"holdout_start":None,
            "baseline_mae":None,"candidate_mae":None,
            "candidate_minus_baseline_mae":None,
            "live_model_unchanged":True,"validated_for_production":False}
    if len(days)<minimum_dates or len(observations)<2*minimum_test:return result
    splits=[]
    for day in days[1:]:
        earlier=[x for x in observations if x[0]<day]
        later=[x for x in observations if x[0]>=day]
        if len(earlier)>=minimum_test and len(later)>=minimum_test:
            splits.append((abs(len(later)-len(observations)*.25),day,earlier,later))
    if not splits:return result
    _,day,earlier,holdout=min(splits,key=lambda x:(x[0],x[1]))
    b=mean(abs(x[4]-x[3]) for x in holdout)
    c=mean(abs(x[5]-x[3]) for x in holdout)
    return {**result,"status":"DESCRIPTIVE_CHRONOLOGICAL_HOLDOUT",
            "earlier_samples":len(earlier),"holdout_samples":len(holdout),
            "holdout_start":day,"baseline_mae":round(b,3),
            "candidate_mae":round(c,3),
            "candidate_minus_baseline_mae":round(c-b,3)}

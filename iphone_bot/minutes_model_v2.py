"""Phase 2 research-only minutes candidate and same-game chronological evaluation.

The existing baseline remains unchanged; neither model affects NBA prop
projections. All forecasting features are computed from past completed
player-game logs. Missing starts, foul data, travel, and confirmed rotations
are never guessed.
"""
import math
from collections import defaultdict
from datetime import date
from statistics import mean, median, pstdev

MIN_HISTORY=8
MIN_HOLDOUT=30
MIN_DATES=5


def numeric_minutes(value):
    if isinstance(value,bool):return None
    try:
        value=float(value)
    except (ValueError,TypeError):return None
    return value if math.isfinite(value) and 0<value<=60 else None


def player_history(history,as_of,team=None):
    """Return strictly prior, deduplicated, same-team, date-stamped minutes."""
    valid={}
    for row in history:
        day=row.get("date")
        if not isinstance(day,str) or day>=as_of:continue
        if team is not None and row.get("team")!=team:continue
        try:date.fromisoformat(day)
        except ValueError:continue
        minutes=numeric_minutes(row.get("MIN"))
        if minutes is None:continue
        # Conflicting repeated observations cannot safely be reconciled.
        # A conflicting duplicate must stay excluded even if later rows
        # repeat one of the two values (do not silently restore that date).
        if day not in valid:
            valid[day]=minutes
        elif valid[day] is not None and valid[day]!=minutes:
            valid[day]=None
    return [(d,m) for d,m in sorted(valid.items()) if m is not None]


def forecast(history,as_of,team=None):
    """Pre-registered robust alternative, with no fitted weights or future data."""
    rows=player_history(history,as_of,team)
    n=len(rows)
    result={"status":"INSUFFICIENT_PLAYER_HISTORY","expected_minutes":None,
            "history_games":n,"confirmed_lineup":False,
            "live_adjustment_applied":False,
            "model":"ROBUST_MINUTES_V2_RESEARCH_ONLY",
            "last_observed_date":rows[-1][0] if rows else None}
    if n<MIN_HISTORY:return result
    minutes=[v for _,v in rows]
    last3=minutes[-3:]
    last5=minutes[-5:]
    last10=minutes[-10:]
    # Higher volatility increases shrinkage toward the ten-game median.
    # This candidate is fixed in code and MUST be compared on later games.
    volatility=pstdev(last5)
    raw=.50*mean(last3)+.30*mean(last5)+.20*mean(last10)
    shrink=min(.40,max(0,(volatility-4)/20))
    candidate=(1-shrink)*raw+shrink*median(last10)
    recent_min=min(last5)
    recent_max=max(last5)
    return {**result,"status":"RESEARCH_FORECAST_UNVALIDATED",
            "expected_minutes":round(max(0,min(48,candidate)),2),
            "observed_last5":round(mean(last5),2),
            "observed_last10":round(mean(last10),2),
            "last5_volatility":round(volatility,2),
            "median_last10":round(median(last10),2),
            "recent_min":round(recent_min,2),"recent_max":round(recent_max,2),
            "requires_lineup_review":True}


def backtest(all_games,minimum_test=MIN_HOLDOUT,minimum_dates=MIN_DATES):
    """Compare old baseline and V2 on identical later games, grouped by date.

    Both forecasts are recomputed exclusively from games earlier than the
    evaluated date. A full date is a unit in the test split, preventing games
    from the same night appearing on opposite sides of the boundary.
    """
    try:
        from .research_context import minutes_estimate
    except ImportError:
        from research_context import minutes_estimate
    by_player=defaultdict(list)
    for game in all_games:
        if game.get("id") is None or not game.get("team") or not game.get("date"):
            continue
        if numeric_minutes(game.get("MIN")) is None:continue
        by_player[(str(game["id"]),str(game["team"]))].append(game)
    evaluated=[]
    for (pid,team),games in by_player.items():
        games.sort(key=lambda g:g["date"])
        for game in games:
            day=game["date"]
            history=[g for g in games if g["date"]<day]
            baseline=minutes_estimate(history,day).get("expected_minutes")
            candidate=forecast(history,day,team).get("expected_minutes")
            if baseline is None or candidate is None:continue
            actual=numeric_minutes(game.get("MIN"))
            if actual is None:continue
            evaluated.append((day,pid,team,actual,float(baseline),float(candidate)))
    evaluated.sort()
    dates=sorted(set(x[0] for x in evaluated))
    base={"status":"INSUFFICIENT_CHRONOLOGICAL_MINUTES_SAMPLES",
          "eligible_samples":len(evaluated),"distinct_dates":len(dates),
          "holdout_samples":0,"earlier_samples":0,
          "holdout_start":None,"baseline_mae":None,"candidate_mae":None,
          "candidate_minus_baseline_mae":None,
          "candidate_improved":0,"candidate_worsened":0,"tied":0,
          "live_model_unchanged":True,"production_adjustment_applied":False,
          "notice":"Player-game evaluations require at least eight prior same-team games; no current injury report is retroactively applied."}
    if len(dates)<minimum_dates or len(evaluated)<minimum_test+minimum_test:
        return base
    options=[]
    for split_day in dates[1:]:
        earlier=[x for x in evaluated if x[0]<split_day]
        holdout=[x for x in evaluated if x[0]>=split_day]
        if len(earlier)>=minimum_test and len(holdout)>=minimum_test:
            options.append((abs(len(holdout)-len(evaluated)*.25),split_day,earlier,holdout))
    if not options:return base
    _,split_day,earlier,holdout=min(options,key=lambda x:(x[0],x[1]))
    baseline_mae=mean(abs(x[4]-x[3]) for x in holdout)
    candidate_mae=mean(abs(x[5]-x[3]) for x in holdout)
    improved=sum(abs(x[5]-x[3])<abs(x[4]-x[3]) for x in holdout)
    worsened=sum(abs(x[5]-x[3])>abs(x[4]-x[3]) for x in holdout)
    return {**base,"status":"CHRONOLOGICAL_RESEARCH_HOLDOUT",
            "holdout_start":split_day,"earlier_samples":len(earlier),
            "holdout_samples":len(holdout),
            "baseline_mae":round(baseline_mae,3),
            "candidate_mae":round(candidate_mae,3),
            "candidate_minus_baseline_mae":round(candidate_mae-baseline_mae,3),
            "candidate_improved":improved,"candidate_worsened":worsened,
            "tied":len(holdout)-improved-worsened,
            "validated_for_production":False}

"""Pregame-only rebound opportunity challenger. Never modify live AI.

The rule is fixed BEFORE prospective grading. Rebound prediction is projected
minutes x a season-shrunk rate based ONLY on completed same-team games before
the event's local date. Robust medians reduce the effect of extreme outings.
No rebound-chance API is silently substituted by game box-score rebounds.
"""
from datetime import date
from statistics import mean,median,pstdev
import math

MIN_HISTORY=8
BLEND=0.30
MAX_SHIFT=0.12

def valid(value):
    if value is None or isinstance(value,bool):return None
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,OverflowError,TypeError):return None

def forecast(history,*,team,event_date,baseline,expected_minutes=None):
    base={"status":"NO_QUALIFIED_REBOUND_SAMPLE","projection":None,
          "research_only":True,"live_applied":False,
          "not_rebound_chance_tracking":True,"probability_calibrated":False}
    baseline=valid(baseline)
    if baseline is None:return {**base,"status":"INVALID_BASELINE"}
    try:date.fromisoformat(event_date)
    except (ValueError,TypeError):return {**base,"status":"INVALID_EVENT_DATE"}
    seen={}
    for row in history:
        if not isinstance(row,dict) or row.get("team")!=team:continue
        day=row.get("date")
        if not isinstance(day,str) or day>=event_date:continue
        mins=valid(row.get("MIN"));reb=valid(row.get("REB"))
        if mins is None or not 8<=mins<=60 or reb is None or reb>55:continue
        try:date.fromisoformat(day)
        except ValueError:continue
        record=(round(mins,5),round(reb,5))
        if day in seen and seen[day]!=record:seen[day]=None
        elif day not in seen:seen[day]=record
    past=[(day,v) for day,v in sorted(seen.items()) if v is not None]
    if len(past)<MIN_HISTORY:
        return {**base,"status":"INSUFFICIENT_PRIOR_GAMES",
            "prior_games":len(past)}
    recent=[x[1] for x in past[-5:]]
    minutes5=[r[0] for r in recent]
    volatility=pstdev(minutes5)
    # A volatile/low-minute role makes a derived rebound volume unreliable.
    if volatility>8:
        return {**base,"status":"UNSTABLE_MINUTES_ROLE",
            "prior_games":len(past),"last5_minutes_sd":round(volatility,3)}
    if min(minutes5)<12:
        return {**base,"status":"LOW_MINUTES_ROTATION",
            "prior_games":len(past)}
    minute_projection=valid(expected_minutes)
    if minute_projection is None or not 10<=minute_projection<=42:
        # Only use known prior minutes, never actual minutes from target game.
        minute_projection=.6*median(minutes5)+.4*mean([v[0] for _,v in past[-10:]])
        minute_method="STRICTLY_PAST_ROBUST_MINUTES_FALLBACK"
    else:
        minute_method="FROZEN_PREGAME_MINUTES_FORECAST"
    # Season and most recent 5 rates; median is robust to unusual totals.
    all_rates=[r[1]/r[0] for _,r in past]
    season_rate=sum(r[1] for _,r in past)/sum(r[0] for _,r in past)
    last5_rate=median(all_rates[-5:])
    # 65% season/exposure rate, 35% recent median. No opponent rebound
    # opportunities claimed without a real, separately verified feed.
    rate=.65*season_rate+.35*last5_rate
    raw=minute_projection*rate
    candidate=baseline+BLEND*(raw-baseline)
    limit=MAX_SHIFT*max(1,baseline)
    output=max(0,min(baseline+limit,max(baseline-limit,candidate)))
    return {**base,"status":"PRETIP_REBOUND_OPPORTUNITY_SHADOW",
        "projection":round(output,4),"raw_projection":round(raw,4),
        "baseline":round(baseline,4),"prior_games":len(past),
        "prior_latest_game":past[-1][0],
        "predicted_minutes":round(minute_projection,3),
        "minutes_method":minute_method,
        "last5_minutes_sd":round(volatility,3),
        "season_rebounds_per36":round(36*season_rate,4),
        "recent_median_rebounds_per36":round(36*last5_rate,4),
        "method":"SEASON_65_RECENT_MEDIAN_35_WITH_30PCT_BLEND_CAPPED_12PCT",
        "source":"HISTORICAL_PLAYER_BOX_SCORES_BEFORE_EVENT_ONLY"}

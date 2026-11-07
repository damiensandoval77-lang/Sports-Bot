"""Fixed assist-specific research challenger, pregame only.

Pre-register the candidate before grading future NBA games. A conservative
forecast uses recent per-minute assists, expected minutes, and role stability.
It NEVER uses any game played on or after the target date, the final boxscore,
or a simulated probability. It does not modify the production AI.
"""
import math
from statistics import median,pstdev

MIN_GAMES=8
MINUTES_CAP=(10.0,42.0)
BLEND=.30
MAX_CHANGE=.20

def finite(v):
    if v is None or isinstance(v,bool):return None
    try:
        n=float(v)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):return None

def assist_shadow(history,day,team,combined,expected_minutes):
    base=finite(combined)
    minutes=finite(expected_minutes)
    rows=sorted((g for g in history if g.get("date","")<day
                 and g.get("team")==team),key=lambda r:r["date"])
    info={"status":"INSUFFICIENT_PREGAME_ASSIST_DATA",
          "projection":None,"prior_games":len(rows),
          "latest_prior_date":rows[-1]["date"] if rows else None,
          "source":"PREGAME_PRIOR_SAME_TEAM_GAME_LOGS",
          "live_applied":False}
    if base is None or minutes is None or not MINUTES_CAP[0]<=minutes<=MINUTES_CAP[1]:
        return {**info,"status":"INVALID_BASELINE_OR_MINUTES"}
    valid_rows=[]
    for row in rows:
        mins=finite(row.get("MIN"))
        assists=finite(row.get("AST"))
        if mins is not None and 5<=mins<=60 and assists is not None:
            valid_rows.append((mins,assists))
    if len(valid_rows)<MIN_GAMES:return info
    last=valid_rows[-10:]
    last5=valid_rows[-5:]
    # Median prior assist/minute opportunity resists exceptional outliers.
    observed_rates=[a/m for m,a in last]
    recent_rate=median(observed_rates)
    per_game_assists=[a for _,a in last5]
    volatility=pstdev(per_game_assists)
    recent_mins=[m for m,_ in last5]
    if pstdev(recent_mins)>7.0:
        return {**info,"status":"UNSTABLE_RECENT_MINUTES_ROLE",
                "prior_games":len(valid_rows)}
    if volatility>3.5:
        return {**info,"status":"HIGH_ASSIST_VOLATILITY",
                "prior_games":len(valid_rows)}
    raw=recent_rate*minutes
    candidate=base+BLEND*(raw-base)
    bound=max(1.,base)*MAX_CHANGE
    candidate=max(0.,min(base+bound,max(base-bound,candidate)))
    return {**info,"status":"PREGAME_LOCKED_ASSIST_CHALLENGER",
       "projection":round(candidate,4),
       "prior_games":len(valid_rows),"median_assists_per_minute":round(recent_rate,5),
       "raw_assist_forecast":round(raw,4),
       "last5_assists_sd":round(volatility,3),
       "expected_minutes":round(minutes,3),
       "method":"FIXED_30PCT_HISTORICAL_RATE_BOUNDED_20PCT"}

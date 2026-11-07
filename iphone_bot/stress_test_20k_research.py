"""Conditional 20,000-draw sensitivity study. NEVER a calibrated win chance.

Independent pregame player-game history only; no sportsbook API or post-tip data.
Keeps the frozen Combined projection and quote unchanged. Every listed scenario
is hypothetical and uses the *same* 20,000 seeded historical rate deviations.
"""
import hashlib
import math
import random
from statistics import mean, pstdev

try:
    from .sanity_shadow_research import past_games, finite, utc, MARKETS
except ImportError:
    from sanity_shadow_research import past_games, finite, utc, MARKETS

DRAWS=20_000
MIN_GAMES=8
METHOD="RESEARCH_PLAYER_RATE_RESIDUAL_BOOTSTRAP_20K_STRESS_V1"
MAX_HISTORY=15
SCENARIOS=(
    ("BASELINE",0.,1.),
    ("MINUTES_PLUS_3",3.,1.),
    ("MINUTES_MINUS_3",-3.,1.),
    ("VARIANCE_PLUS_50PCT",0.,1.5),
    ("MINUTES_PLUS_3_VARIANCE_PLUS_50PCT",3.,1.5),
    ("MINUTES_MINUS_3_VARIANCE_PLUS_50PCT",-3.,1.5),
)

def check(history,*,team,market,projection,line,event_start,captured_at,
          expected_minutes=None,injury_status=None,injury_source=None,
          player_id=None):
    result={"method":METHOD,"status":"INSUFFICIENT_PREGAME_HISTORY",
            "simulation_draws_per_scenario":DRAWS,"simulated_scenarios":{},
            "raw_baseline_conditional_hit_probability":None,
            "worst_case_conditional_hit_probability":None,
            "confidence_drop_percentage_points":None,
            "fragile_high_confidence":False,"warnings":[],
            "probabilities_calibrated":False,"research_only":True,
            "live_projection_modified":False,"live_probability_modified":False,
            "production_picks_modified":False,
            "limitation":"Conditional sensitivity is not validated real-market probability."}
    if market not in MARKETS:
        return {**result,"status":"UNSUPPORTED_MARKET"}
    p,threshold,mins=finite(projection),finite(line),finite(expected_minutes)
    if p is None or threshold is None or mins is None or not 5<=mins<=48:
        return {**result,"status":"INVALID_OR_MISSING_INPUTS",
                "warnings":["MISSING_VALID_FORECAST_LINE_OR_MINUTES"]}
    try:
        if utc(captured_at)>=utc(event_start):
            return {**result,"status":"LATE_CAPTURE_REJECTED"}
        samples=past_games(history,team,market,event_start,captured_at)
    except (ValueError,TypeError,KeyError):
        return {**result,"status":"INVALID_TIME"}
    if len(samples)<MIN_GAMES:
        return {**result,"history_games":len(samples),
                "warnings":["INSUFFICIENT_CURRENT_SEASON_HISTORY"]}
    samples=samples[-MAX_HISTORY:]
    rates=[value/minutes for _,value,minutes in samples]
    average=mean(rates)
    sigma=pstdev(rates)
    if sigma<1e-6:
        return {**result,"status":"INSUFFICIENT_HISTORICAL_VARIABILITY",
                "history_games":len(samples),
                "warnings":["NEAR_ZERO_OBSERVED_RATE_VARIATION"]}
    warnings=[]
    if (str(injury_status).upper()!="AVAILABLE" or
            injury_source!="OFFICIAL_NBA_REPORT"):
        warnings.append("UNVERIFIED_INJURY_OR_LINEUP")
    observed_minutes=mean(row[2] for row in samples[-5:])
    if abs(mins-observed_minutes)>5:
        warnings.append("MINUTES_DISAGREE_WITH_RECENT_HISTORY")
    if pstdev(row[2] for row in samples[-5:])>6:
        warnings.append("HIGH_MINUTES_VOLATILITY")
    if (utc(captured_at).date()-__import__("datetime").date.fromisoformat(samples[-1][0])).days>14:
        warnings.append("STALE_PLAYER_HISTORY")
    # Predefined side: no optimizing which side looks strongest after draws.
    if p==threshold:
        return {**result,"status":"NO_PROJECTED_SIDE"}
    side="OVER" if p>threshold else "UNDER"
    seed_key="|".join((str(player_id or ""),team,market,
        utc(event_start).isoformat(),utc(captured_at).isoformat(),
        f"{p:.6f}",f"{threshold:.6f}"))
    rng=random.Random(int(hashlib.sha256(seed_key.encode()).hexdigest()[:16],16))
    deviations=[(rates[rng.randrange(len(rates))]-average) for _ in range(DRAWS)]
    scenario_probs={}
    for name,shift,scale in SCENARIOS:
        scenario_minutes=max(5.,min(48.,mins+shift))
        center=p*scenario_minutes/mins
        wins=0
        pushes=0
        for d in deviations:
            projected=max(0.,center+d*scenario_minutes*scale)
            if abs(projected-threshold)<1e-9:
                pushes+=1
            elif (projected>threshold)==(side=="OVER"):
                wins+=1
        probability=(wins+.5)/(DRAWS+1)
        scenario_probs[name]={"minutes_assumption":round(scenario_minutes,2),
             "variance_multiplier":scale,
             "conditional_hit_probability":round(probability,4),
             "push_probability":round(pushes/DRAWS,4)}
    raw=scenario_probs["BASELINE"]["conditional_hit_probability"]
    worst=min(x["conditional_hit_probability"] for x in scenario_probs.values())
    drop=round(100*(raw-worst),2)
    fragile=(raw>=.9 and (worst<.75 or drop>=15))
    if fragile:warnings.append("FRAGILE_HIGH_SIMULATED_CONFIDENCE")
    return {**result,"status":"CONDITIONAL_STRESS_RESEARCH_ONLY",
        "history_games":len(samples),"projected_side":side,
        "recent_minutes_average":round(observed_minutes,2),
        "expected_minutes_assumption":round(mins,2),
        "historical_rate_std":round(sigma,5),
        "simulated_scenarios":scenario_probs,
        "raw_baseline_conditional_hit_probability":raw,
        "worst_case_conditional_hit_probability":worst,
        "confidence_drop_percentage_points":drop,
        "fragile_high_confidence":fragile,"warnings":warnings}

"""Assist V2 research-only probabilistic forecast. No production mutation.

Inputs must be assembled from information available strictly before tipoff.
Unavailable opportunity/teammate inputs remain missing, never inferred.
"""
import math
import random
from statistics import median, pstdev

def _num(x):
    try:
        y = float(x)
        return y if math.isfinite(y) and y >= 0 else None
    except (TypeError, ValueError):
        return None

def _clip(x, lo, hi):
    return max(lo, min(hi, x))

def forecast(history, target_date, team, expected_minutes, baseline=None,
             potential_assists_per_min=None, conversion_rate=None,
             teammate_out_adjustment=None, opponent_factor=None,
             pace_factor=None, line=None, simulations=20000, seed=17):
    """Return forecast and Monte Carlo probability; only strictly prior logs.

    Optional external factors must be pregame snapshots. Adjustments are capped
    to avoid claiming unsupported injury or matchup effects.
    """
    mins = _num(expected_minutes)
    base = _num(baseline)
    info = {"status": "INSUFFICIENT_PREGAME_DATA", "live_applied": False,
            "model": "assist_v2_research", "simulations": 0}
    if mins is None or not 8 <= mins <= 45:
        return {**info, "status": "INVALID_EXPECTED_MINUTES"}
    rows = []
    for g in history:
        if str(g.get("date", "")) >= str(target_date) or g.get("team") != team:
            continue
        m, a = _num(g.get("MIN")), _num(g.get("AST"))
        if m is not None and a is not None and 5 <= m <= 60:
            rows.append((str(g["date"]), m, a))
    rows.sort(key=lambda x: x[0])
    if len(rows) < 8:
        return {**info, "prior_games": len(rows)}
    last = rows[-12:]
    recent = last[-5:]
    if pstdev([r[1] for r in recent]) > 8:
        return {**info, "status": "UNSTABLE_MINUTES", "prior_games": len(rows)}
    # Shrink the recent per-minute rate toward the longer prior sample.
    long_rate = sum(r[2] for r in last) / sum(r[1] for r in last)
    short_rate = sum(r[2] for r in recent) / sum(r[1] for r in recent)
    rate = .65 * long_rate + .35 * short_rate
    rate_estimate = rate * mins
    pa = _num(potential_assists_per_min)
    conv = _num(conversion_rate)
    if pa is not None and conv is not None and 0 <= conv <= 1:
        opportunity_estimate = mins * pa * conv
        rate_estimate = .65 * rate_estimate + .35 * opportunity_estimate
    # Adjustments default to neutral, not fabricated from unknown lineups.
    factors = []
    for val, lo, hi in ((teammate_out_adjustment, .75, 1.25),
                        (opponent_factor, .85, 1.15),
                        (pace_factor, .85, 1.15)):
        v = _num(val)
        factors.append(_clip(v, lo, hi) if v is not None else 1.)
    estimate = rate_estimate * math.prod(factors)
    if base is not None:
        estimate = .75 * estimate + .25 * base
    estimate = _clip(estimate, 0., 20.)
    # Method of moments for count variance, with Poisson fallback.
    scaled = [a * mins / m for _, m, a in last]
    mu = sum(scaled) / len(scaled)
    var = sum((a - mu)**2 for a in scaled) / len(scaled)
    dispersion = mu * mu / (var - mu) if var > mu + .05 else None
    rng = random.Random(seed)
    threshold = _num(line)
    wins = pushes = 0
    n = max(1, int(simulations))
    for _ in range(n):
        lam = rng.gammavariate(dispersion, estimate / dispersion) if dispersion else estimate
        # Exact Poisson draw via inter-arrival exponential sampling.
        t = 0.
        count = 0
        while True:
            t += rng.expovariate(lam) if lam > 0 else float("inf")
            if t > 1:
                break
            count += 1
        if threshold is not None:
            wins += count > threshold
            pushes += count == threshold
    return {"status": "RESEARCH_FORECAST", "model": "assist_v2_research",
            "live_applied": False, "projection": round(estimate, 4),
            "prior_games": len(rows), "latest_prior_date": rows[-1][0],
            "simulations": n, "distribution": "negative_binomial" if dispersion else "poisson",
            "over_probability": round(wins / n, 4) if threshold is not None else None,
            "push_probability": round(pushes / n, 4) if threshold is not None else None,
            "features": {"expected_minutes": mins, "long_rate": round(long_rate, 5),
                         "short_rate": round(short_rate, 5),
                         "opportunity_data_available": pa is not None and conv is not None,
                         "adjustment_factors": factors},
            "limitations": "Uncalibrated research probability; pregame data provenance required"}

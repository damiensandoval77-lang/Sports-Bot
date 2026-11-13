"""Strict price-based edge readiness for NBA props.

Only a calibrated, independently validated COMBINED model with a fresh,
identical-side/line sportsbook quote may pass the verification gate.
A research simulation or unpriced PrizePicks pick'em offer can NEVER
establish positive expected value through this module.
"""
import math
from datetime import datetime, timezone

MIN_INDEPENDENT_OUTCOMES = 300
MIN_EVENT_DATES = 10
MAX_PRICE_AGE_MINUTES = 30
EDGE_BUFFER = 0.02  # additional conservative percentage-points buffer

def american_profit(odds):
    if isinstance(odds, bool): raise ValueError("Invalid odds")
    price=float(odds)
    if not math.isfinite(price) or (-100 < price < 100):
        raise ValueError("American odds must be <= -100 or >= +100")
    return price/100 if price>=100 else 100/abs(price)

def break_even(odds):
    return 1/(1+american_profit(odds))

def evaluate_edge(*, model_probability=None, lower_probability=None,
                  calibration=None, quote=None, side=None, line=None,
                  wager_type="sportsbook", now=None):
    """Return EDGE_READY only when all independent evidence is present.

    lower_probability is a precomputed conservative confidence lower bound,
    evaluated on a *separate* out-of-time sample, NOT estimated from the
    current pick, same-day price, or Monte Carlo draw count.
    """
    reasons=[]
    calibration=calibration or {}
    now=now or datetime.now(timezone.utc)
    if wager_type!="sportsbook":
        reasons.append("PICKEM_PAYOUT_REQUIRES_SLIP_LEVEL_MODEL")
    if calibration.get("model")!="combined" or calibration.get("verified") is not True:
        reasons.append("COMBINED_PROBABILITY_NOT_VALIDATED")
    if (int(calibration.get("independent_outcomes") or 0)<MIN_INDEPENDENT_OUTCOMES or
        int(calibration.get("distinct_event_dates") or 0)<MIN_EVENT_DATES or
        calibration.get("chronological_holdout") is not True or
        calibration.get("frozen_pregame_predictions") is not True):
        reasons.append("INSUFFICIENT_INDEPENDENT_OUT_OF_SAMPLE_VALIDATION")

    try:
        p=float(model_probability)
        lower=float(lower_probability)
        if not (math.isfinite(p) and math.isfinite(lower) and
                0<=lower<=p<=1):
            raise ValueError
    except (ValueError, TypeError):
        p=None
        lower=None
        reasons.append("PROBABILITY_OR_CONSERVATIVE_BOUND_MISSING")

    profit=None
    threshold=None
    conservative_ev=None
    if not isinstance(quote,dict):
        reasons.append("FRESH_EXACT_BOOK_PRICE_MISSING")
    else:
        try:
            quote_side=str(quote["side"]).upper()
            expected_side=str(side).upper()
            if expected_side not in ("OVER","UNDER") or quote_side!=expected_side:
                raise ValueError("SIDE_MISMATCH")
            if float(quote["line"])!=float(line):
                raise ValueError("LINE_MISMATCH")
            updated=datetime.fromisoformat(str(quote["updated_at"]).replace("Z","+00:00"))
            if updated.tzinfo is None: raise ValueError("MISSING_QUOTE_TIMEZONE")
            age=(now-updated.astimezone(timezone.utc)).total_seconds()/60
            if age<0 or age>MAX_PRICE_AGE_MINUTES:
                raise ValueError("QUOTE_STALE_OR_IN_FUTURE")
            profit=american_profit(quote["odds"])
            threshold=1/(1+profit)
            if lower is not None:
                conservative_ev=lower*profit-(1-lower)
                if lower<=threshold+EDGE_BUFFER:
                    reasons.append("CONSERVATIVE_PROBABILITY_DOES_NOT_CLEAR_PRICE")
        except (KeyError, TypeError, ValueError) as exc:
            reasons.append("FRESH_EXACT_BOOK_PRICE_MISSING")
    return {
        "status":"EDGE_READY_FOR_REVIEW" if not reasons else "NO_VERIFIED_EDGE",
        "reasons":list(dict.fromkeys(reasons)),
        "break_even_probability":round(threshold,4) if threshold is not None else None,
        "estimated_probability":round(p,4) if p is not None else None,
        "conservative_lower_probability":round(lower,4) if lower is not None else None,
        "conservative_ev_per_unit":round(conservative_ev,4) if conservative_ev is not None else None,
        "verified_edge":not reasons,
        "method":"CHRONOLOGICAL_COMBINED_PROBABILITY_EXACT_PRICE_GUARD_V1",
        "disclaimer":"EDGE_READY_FOR_REVIEW is not a profit guarantee. Calibration, liquidity, lineup, book limits and quote changes still matter."
    }

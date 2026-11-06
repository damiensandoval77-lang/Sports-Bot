"""Experimental equal-weight consensus of independent NBA model projections.

The median of TWO finite projections is their arithmetic midpoint.
Do not mix a rounded display projection into the calculation.
This is an unvalidated ensemble, not a calibrated sportsbook probability.
"""
import math

METHOD="TWO_MODEL_MEDIAN_EQUAL_WEIGHT_RESEARCH_ONLY"

def combine_projections(original,opponent_aware=None):
    original=float(original)
    if not math.isfinite(original) or original<0:
        raise ValueError("Invalid original AI projection")
    if opponent_aware is None:
        return {"projection":original,"method":"ORIGINAL_AI_FALLBACK",
                "model_count":1,"ensemble_validated":False}
    shadow=float(opponent_aware)
    if not math.isfinite(shadow) or shadow<0:
        raise ValueError("Invalid opponent-aware projection")
    return {"projection":(original+shadow)/2,
            "method":METHOD,"model_count":2,"ensemble_validated":False}

"""Experimental ranking using out-of-time NBA model residuals.

This is NOT a sportsbook-calibrated probability model or a verified chance to
win. Estimates assume future errors resemble past out-of-time box-score errors.
No live odds, vig, payouts, EV or lineup certainty is represented.
"""
import numpy as np

METHOD="CHRONOLOGICAL_VALIDATION_EMPIRICAL_RESIDUALS_UNCALIBRATED"

def probability_sides(prediction,line,residuals):
    """Return empirical over/under/push frequencies given a future game line.

    Residuals must come from future dates excluded from fitting the
    corresponding calibration model. The current live model may be refitted.
    """
    p=float(prediction)
    q=float(line)
    r=np.asarray(residuals,dtype=float)
    r=np.sort(r[np.isfinite(r)])
    if not np.isfinite(p) or not np.isfinite(q) or len(r)<1000:
        raise ValueError("Insufficient independent chronological residual calibration")
    threshold=q-p
    n=len(r)
    # Continuity correction avoids exact 0% / 100% on finite observed samples.
    under=(np.searchsorted(r,threshold,side="left")+.5)/(n+1)
    over=(n-np.searchsorted(r,threshold,side="right")+.5)/(n+1)
    push=max(0.0,1.0-over-under)
    return {"over":float(over),"under":float(under),"push":float(push),
            "sample_size":n,"method":METHOD}

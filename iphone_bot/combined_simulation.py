"""Deterministic 20,000-draw research forecast using chronological residuals.

Residuals are from the ORIGINAL model. Centering them on a COMBINED forecast
is an explicit modeling assumption, NOT verified combined-model calibration.
No market-implied probability, EV or betting edge is claimed.
"""
import hashlib
import numpy as np

METHOD = "COMBINED_PROJECTION_20K_ORIGINAL_RESIDUAL_BOOTSTRAP_UNCALIBRATED"
DRAWS = 20000

def simulate_combined_hit_rate(combined_projection, line, residuals, identity, draws=DRAWS):
    center = float(combined_projection)
    threshold = float(line)
    errors = np.asarray(residuals, dtype=float)
    errors = errors[np.isfinite(errors)]
    if not (np.isfinite(center) and np.isfinite(threshold)) or len(errors) < 1000:
        raise ValueError("Chronological residual validation sample unavailable")
    if draws != DRAWS:
        raise ValueError("Research simulation count must be 20,000")
    seed = int.from_bytes(hashlib.sha256(str(identity).encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    simulated = np.maximum(0.0, center + rng.choice(errors, size=draws, replace=True))
    over = int(np.count_nonzero(simulated > threshold))
    under = int(np.count_nonzero(simulated < threshold))
    push = draws - over - under
    direction = "Over" if center > threshold else "Under" if center < threshold else "Neutral"
    hit = over if direction == "Over" else under if direction == "Under" else None
    return {
        "method": METHOD, "simulation_count": draws,
        "over_hit_rate": round(over / draws, 4),
        "under_hit_rate": round(under / draws, 4),
        "push_rate": round(push / draws, 4),
        "direction": direction,
        "selected_hit_rate": round(hit / draws, 4) if hit is not None else None,
        "calibrated": False,
        "residual_provenance": "ORIGINAL_MODEL_CHRONOLOGICAL_HOLDOUT",
        "combined_residuals_validated": False,
        "independent_game_outcomes": False
    }

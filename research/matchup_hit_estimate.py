"""Research-only matchup probability engine. NOT wired to live picks.
All factors and residual errors must be available at pretip freeze time.
No historical sportsbook hit rates, posttip data or unsupported probabilities.
"""
from datetime import datetime, timezone
from math import isfinite

REQUIRED = ("opponent_position_defense", "projected_minutes",
            "usage_opportunities", "teammate_availability", "depth_role",
            "pace_possessions")


def _time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp missing")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def _number(value, label, positive=False, signed=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(label + " must be finite")
    if (positive and value <= 0) or (not positive and not signed and value < 0):
        raise ValueError(label + " invalid")
    return float(value)


def estimate(*, projection, line, side, tipoff, captured_at,
             factors, residuals, model_id, stat):
    """Provisional scenario probability. Ratio effects are not fitted or calibrated.

    Each factor is a verified pretip baseline and matchup value with source
    and observed_at. Residual errors must come from earlier, independent,
    chronological model validation, not exact-line historical win rates.
    All six ratios are applied multiplicatively as an explicit research
    hypothesis; the combined effect can double-count correlated changes,
    so outputs must never be promoted without paired validation.
    """
    start, locked = _time(tipoff), _time(captured_at)
    if locked >= start:
        raise ValueError("not frozen pretip")
    if side not in ("OVER", "UNDER") or not model_id or not stat:
        raise ValueError("direction, model and stat required")
    mu = _number(projection, "projection")
    threshold = _number(line, "standard line")
    if not isinstance(factors, dict) or set(factors) != set(REQUIRED):
        raise ValueError("required matchup factors missing or unrecognized")
    ratio, trace = 1.0, {}
    for key in REQUIRED:
        item = factors[key]
        if not isinstance(item, dict) or not isinstance(item.get("source"), str) or not item["source"]:
            raise ValueError(key + " source missing")
        observed = _time(item.get("observed_at"))
        if observed > locked:
            raise ValueError(key + " available after freeze")
        before = _number(item.get("baseline"), key + " baseline", positive=True)
        after = _number(item.get("matchup"), key + " matchup", positive=True)
        factor = after / before
        ratio *= factor
        trace[key] = {"ratio": factor, "source": item["source"],
                      "observed_at": item["observed_at"]}
    if not isinstance(residuals, list) or len(residuals) < 30:
        raise ValueError("insufficient validation residuals")
    errors = []
    for item in residuals:
        if not isinstance(item, dict) or not item.get("source") or "line_hit" in item:
            raise ValueError("validation residual provenance missing")
        if _time(item.get("observed_at")) > locked:
            raise ValueError("future validation residual")
        errors.append(_number(item.get("error"), "validation error", signed=True))
    adjusted = mu * ratio
    modeled = [max(0.0, adjusted + error) for error in errors]
    wins = sum((v > threshold if side == "OVER" else v < threshold)
               for v in modeled)
    pushes = sum(v == threshold for v in modeled)
    return {"model_id": model_id, "stat": stat, "direction": side,
            "original_line": threshold, "baseline_projection": mu,
            "matchup_projection": adjusted,
            "modeled_selected_probability": wins / len(modeled),
            "modeled_push_probability": pushes / len(modeled),
            "residual_sample_size": len(modeled), "factors": trace,
            "calibrated": False, "research_only": True,
            "opponent_aware_provenance_present": True,
            "note": "Uncalibrated opponent-conditioned research hypothesis only; "
                    "verify against frozen pregame outcomes before promotion."}

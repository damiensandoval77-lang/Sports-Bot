"""Offline-only audit of saved pregame confidence coverage and prospective readiness.

Original-model residual probabilities are proxies, NOT verified Combined AI
confidence. This module never backfills probabilities or changes live picks.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

try:
    from .combined_probability_audit import locked, describe, METHOD
    from .paper_pick_pipeline import utc
except ImportError:
    from combined_probability_audit import locked, describe, METHOD
    from paper_pick_pipeline import utc

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/paper_pick_ledger.json"
OUT = ROOT / "docs/confidence_readiness_research.json"
STATS = ("PTS", "REB", "AST", "PRA")
BANDS = (("50-60%", .5, .6), ("60-70%", .6, .7),
         ("70-80%", .7, .8), ("80-90%", .8, .9),
         ("90-100%", .9, 1.00000001))


def finite(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def valid_pregame_proxy(row):
    try:
        if utc(row["captured_at"]) >= utc(row["event_start"]):
            return False
    except (KeyError, ValueError, TypeError):
        return False
    p, line, proj = (finite(row.get(k)) for k in
                     ("combined_probability_proxy_estimate", "line", "combined_projection"))
    if p is None or not 0 <= p <= 1 or line is None or proj is None:
        return False
    side = "OVER" if proj > line else "UNDER" if proj < line else None
    return (side is not None and side == row.get("side")
            and side == row.get("combined_probability_proxy_side")
            and row.get("combined_probability_proxy_method") == METHOD)


def pending_diagnostics(records, now):
    """Classify frozen candidates without guessing whether box scores are final."""
    current = utc(now)
    buckets = {"before_tipoff": 0, "tipped_off_under_two_hours": 0,
               "past_two_hours_unsettled": 0, "settled_with_proxy": 0,
               "settled_without_proxy": 0, "invalid_capture_or_proxy": 0}
    dates = {}
    for row in records:
        status = row.get("status")
        if status == "SETTLED":
            bucket = "settled_with_proxy" if valid_pregame_proxy(row) else "settled_without_proxy"
        elif status != "PENDING" or not valid_pregame_proxy(row):
            bucket = "invalid_capture_or_proxy"
        else:
            try:
                start = utc(row["event_start"])
            except (KeyError, TypeError, ValueError):
                bucket = "invalid_capture_or_proxy"
            else:
                delta = (current - start).total_seconds()
                bucket = ("before_tipoff" if delta < 0 else
                          "tipped_off_under_two_hours" if delta < 7200 else
                          "past_two_hours_unsettled")
                day = start.date().isoformat()
                date_counts = dates.setdefault(day, {"before_tipoff": 0,
                    "tipped_off_under_two_hours": 0, "past_two_hours_unsettled": 0})
                date_counts[bucket] += 1
        buckets[bucket] += 1
    return {"counts": buckets, "pending_by_utc_event_date": dates,
            "notes": ["Elapsed time does not confirm game-final status.",
                      "A settled row without a frozen proxy cannot be backfilled.",
                      "Past-two-hour pending rows require verified final box-score inspection, not automatic grading."]}


def audit(records, now=None):
    """Only first eligible quote per player/game/stat gets a graded observation."""
    observations, excluded = locked(records)
    if now is None:
        now = datetime.now(timezone.utc).isoformat()
    settled = [r for r in records if r.get("status") == "SETTLED"]
    bands = {}
    for label, lo, hi in BANDS:
        subset = [r for r in observations if lo <= r["probability"] < hi]
        bands[label] = {**describe(subset), "verified_confidence": False}
    by_stat = {stat: describe([r for r in observations if r["market"] == stat])
               for stat in STATS}
    dates = len({r["date"] for r in observations})
    return {
        "status": "RESEARCH_ONLY_NOT_CALIBRATED",
        "calibrated": False,
        "publish_as_verified_confidence": False,
        "probability_source": "ORIGINAL_RESIDUAL_PROXY_FOR_COMBINED_DIRECTION",
        "overall": describe(observations),
        "by_stat": by_stat,
        "by_confidence_band": bands,
        "high_confidence_90_plus":
            describe([r for r in observations if r["probability"] >= .9]),
        "coverage": {
            "total_quote_records": len(records),
            "settled_quote_records": len(settled),
            "settled_missing_frozen_probability": sum(
                finite(r.get("combined_probability_proxy_estimate")) is None
                for r in settled),
            "pregame_quotes_with_valid_frozen_proxy": sum(
                r.get("status") in ("PENDING", "SETTLED") and valid_pregame_proxy(r)
                for r in records),
            "eligible_independent_settled_observations": len(observations),
            "eligible_distinct_game_dates": dates,
        },
        "excluded": excluded,
        "pending_diagnostics": pending_diagnostics(records, now),
        "ready_to_fit_calibration": (
            len(observations) >= 500 and dates >= 20 and
            all(by_stat[s]["sample_size"] >= 50 for s in STATS)),
        "limitations": [
            "Missing historical probabilities cannot be reconstructed after games.",
            "Residual probabilities are original-model proxies, not Combined AI confidence.",
            "Props from one game are correlated; readiness thresholds are preliminary.",
            "Fit only on earlier dates, test on later unseen dates, then validate prospectively.",
            "No calibration, changes to production picks, or accuracy gains are claimed."
        ],
    }


def main():
    records = json.loads(LEDGER.read_text()).get("records", [])
    result = audit(records)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"coverage": result["coverage"],
                      "ready_to_fit_calibration": result["ready_to_fit_calibration"],
                      "pending_diagnostics": result["pending_diagnostics"]["counts"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()

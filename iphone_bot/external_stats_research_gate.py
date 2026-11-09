"""Read-only promotion gate for NBA research model changes.

Consumes existing frozen paper_results summary. A green test suite is not
evidence of live predictive gain. Never rewrite predictions, prices, or grades.
Aggregate model summaries are NOT substitute paired challenger observations.
"""
import json
import math
from pathlib import Path

MIN_DATES = 10
MIN_PAIRED = 100
TARGETS = ("PTS", "REB", "AST", "PRA")


def _nonnegative_int(value):
    try:
        n = int(value)
        return n if n >= 0 else 0
    except (ValueError, TypeError, OverflowError):
        return 0


def readiness(paper, paired=None):
    perf = paper.get("performance") or {}
    models = perf.get("models") or {}
    feedback = paper.get("accuracy_feedback") or {}
    days = _nonnegative_int(((feedback.get("overall") or {}).get("overall") or {}).get("distinct_game_dates"))
    combined = models.get("combined") or {}
    n = _nonnegative_int(combined.get("direction_eligible"))
    hit = combined.get("direction_hit_rate")
    roi = combined.get("paper_roi_per_priced_unit")
    try:
        rate, return_rate = float(hit), float(roi)
        valid = math.isfinite(rate) and 0 <= rate <= 1 and math.isfinite(return_rate)
    except (TypeError, ValueError):
        valid = False
        rate = return_rate = None
    if not valid:
        rate = return_rate = None
    paired_valid = (isinstance(paired, dict)
                    and paired.get("status") == "PAIRED_SHADOW_RESEARCH_ONLY"
                    and paired.get("production_modified") is False
                    and paired.get("automatic_promotion") is False
                    and _nonnegative_int(paired.get("paired_rows")) >= MIN_PAIRED
                    and _nonnegative_int(paired.get("unique_event_dates")) >= MIN_DATES)
    reasons = []
    if days < MIN_DATES:
        reasons.append("INSUFFICIENT_INDEPENDENT_SETTLED_GAME_DATES")
    if n < MIN_PAIRED or rate is None:
        reasons.append("INSUFFICIENT_OR_INVALID_GRADED_BASELINE")
    if not paired_valid:
        reasons.append("NO_SUFFICIENT_POINT_IN_TIME_PAIRED_CHALLENGER")
    if rate is None or return_rate is None or return_rate <= 0:
        reasons.append("NO_DEMONSTRATED_POSITIVE_PAPER_PERFORMANCE")
    # Even with a positive historical result, automatic promotion is prohibited.
    return {
        "status": "RESEARCH_PROMOTION_BLOCKED",
        "promotion_allowed": False,
        "production_modified": False,
        "reason_codes": reasons or ["REQUIRES_PROSPECTIVE_HUMAN_REVIEW_AND_CALIBRATION"],
        "observed_baseline": {
            "independent_settled_game_dates": days,
            "direction_eligible": n,
            "combined_direction_hit_rate": rate,
            "combined_paper_roi_per_priced_unit": return_rate,
        },
        "paired_comparison_gate_met": bool(paired_valid),
        "minimum_independent_dates": MIN_DATES,
        "minimum_paired_predictions": MIN_PAIRED,
        "warnings": [
            "Aggregate paper ROI is not a paired challenger backtest.",
            "Correlated props cannot be treated as independent betting trials.",
            "No current-season licensed third-party data is assumed available.",
            "Past results do not establish a profitable betting edge."
        ],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", default="docs/paper_results.json")
    parser.add_argument("--paired", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    paper = json.loads(Path(args.paper).read_text(encoding="utf-8"))
    paired = json.loads(Path(args.paired).read_text(encoding="utf-8")) if args.paired else None
    report = readiness(paper, paired)
    content = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content+"\n", encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()

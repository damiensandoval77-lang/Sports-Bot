"""Paired, point-in-time evaluation of baseline and shadow NBA forecasts.

Never trains on test outcomes, invents missing quotes, or promotes a challenger.
Both forecast timestamps must precede the event. Metrics are on common rows only.
Input CSV columns: game_id, player_id, market, event_start,
 baseline_captured_at, challenger_captured_at, baseline_projection,
 challenger_projection, actual.
Optional columns: line, baseline_over_probability, challenger_over_probability.
"""
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

MARKETS = frozenset(("PTS", "REB", "AST", "PRA"))
REQUIRED = frozenset(("game_id", "player_id", "market", "event_start",
    "baseline_captured_at", "challenger_captured_at", "baseline_projection",
    "challenger_projection", "actual"))
MIN_PAIRS = 100
MIN_DATES = 10


class ComparisonError(ValueError):
    pass


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ComparisonError("Invalid event or forecast timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ComparisonError("Timezone-aware timestamps required")
    return parsed.astimezone(timezone.utc)


def number(value, label):
    try:
        v = float(value)
    except (ValueError, TypeError) as exc:
        raise ComparisonError("Missing or invalid " + label) from exc
    if not math.isfinite(v):
        raise ComparisonError("Nonfinite " + label)
    return v


def _metrics(rows, column):
    errors = [r[column] - r["actual"] for r in rows]
    return {
        "n": len(rows),
        "mae": round(sum(abs(e) for e in errors) / len(rows), 5),
        "rmse": round(math.sqrt(sum(e * e for e in errors) / len(rows)), 5),
        "bias": round(sum(errors) / len(rows), 5),
    }


def compare(rows, *, min_pairs=MIN_PAIRS, min_dates=MIN_DATES):
    validated = []
    seen = set()
    by_date = set()
    for raw in rows:
        if not REQUIRED.issubset(raw):
            raise ComparisonError("Missing required comparison fields")
        event = timestamp(raw["event_start"])
        if timestamp(raw["baseline_captured_at"]) >= event:
            raise ComparisonError("Baseline forecast not captured pregame")
        if timestamp(raw["challenger_captured_at"]) >= event:
            raise ComparisonError("Challenger forecast not captured pregame")
        market = str(raw["market"])
        if market not in MARKETS:
            raise ComparisonError("Unsupported market")
        game_id, player_id = str(raw["game_id"]).strip(), str(raw["player_id"]).strip()
        if not game_id or not player_id:
            raise ComparisonError("Verified game and player identifiers required")
        key = (game_id, player_id, market)
        if key in seen:
            raise ComparisonError("Duplicate player/game/market comparison")
        seen.add(key)
        baseline = number(raw["baseline_projection"], "baseline projection")
        challenger = number(raw["challenger_projection"], "challenger projection")
        actual = number(raw["actual"], "actual")
        if min(baseline, challenger, actual) < 0:
            raise ComparisonError("Negative projections or outcomes")
        item = {"market": market, "baseline": baseline, "challenger": challenger,
                "actual": actual, "date": event.date().isoformat()}
        optional = ("line", "baseline_over_probability", "challenger_over_probability")
        if all(raw.get(k) not in (None, "") for k in optional):
            line = number(raw["line"], "line")
            pb = number(raw["baseline_over_probability"], "baseline probability")
            pc = number(raw["challenger_over_probability"], "challenger probability")
            if line < 0 or not (0 <= pb <= 1 and 0 <= pc <= 1):
                raise ComparisonError("Invalid sportsbook line or probability")
            # Exact pushes are excluded from over/under calibration; no label.
            if actual != line:
                item["over_outcome"] = int(actual > line)
                item["baseline_over_probability"] = pb
                item["challenger_over_probability"] = pc
        validated.append(item)
        by_date.add(item["date"])
    if len(validated) < min_pairs or len(by_date) < min_dates:
        raise ComparisonError("Insufficient paired pregame predictions or distinct dates")
    grouped = defaultdict(list)
    for item in validated:
        grouped[item["market"]].append(item)
    output = {}
    for market, sample in sorted(grouped.items()):
        base = _metrics(sample, "baseline")
        challenge = _metrics(sample, "challenger")
        qualified = [r for r in sample if "over_outcome" in r]
        calibration = None
        if qualified:
            calibration = {
                "n": len(qualified),
                "baseline_brier": round(sum((r["baseline_over_probability"] - r["over_outcome"]) ** 2 for r in qualified) / len(qualified), 6),
                "challenger_brier": round(sum((r["challenger_over_probability"] - r["over_outcome"]) ** 2 for r in qualified) / len(qualified), 6),
                "calibrated": False,
            }
        output[market] = {
            "baseline": base, "challenger": challenge,
            "mae_delta_challenger_minus_baseline": round(challenge["mae"] - base["mae"], 5),
            "brier_comparison": calibration,
            "market_sample_sufficient": len(sample) >= min_pairs,
        }
    return {
        "status": "PAIRED_SHADOW_RESEARCH_ONLY",
        "paired_rows": len(validated),
        "unique_event_dates": len(by_date),
        "markets": output,
        "production_modified": False,
        "automatic_promotion": False,
        "calibrated": False,
        "warning": "Paired errors alone do not establish betting profitability or probability calibration.",
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Timestamped paired CSV; no live data fetched")
    parser.add_argument("--output", required=True, help="Write research comparison JSON")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8-sig", newline="") as stream:
        result = compare(csv.DictReader(stream))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "paired_rows": result["paired_rows"],
                      "unique_event_dates": result["unique_event_dates"]}))


if __name__ == "__main__":
    main()

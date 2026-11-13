"""Read-only integrity check for pregame snapshots and final grades.

Does not assert live API availability or deployment health. Never changes data.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID = {"PENDING", "SETTLED", "VOID_DNP", "INVALID_LATE_CAPTURE"}


def audit(data, now=None):
    now = now or datetime.now(timezone.utc)
    errors, warnings = [], []
    sampled = "records" not in data
    records = data.get("records", data.get("results", []))
    if not isinstance(records, list):
        return {"status": "FAIL", "errors": ["records must be a list"], "warnings": []}
    counts = {status: 0 for status in VALID}
    seen = set()
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            errors.append(f"row {index}: not an object")
            continue
        status = row.get("status")
        if status not in VALID:
            errors.append(f"row {index}: unknown status")
            continue
        counts[status] += 1
        fields = ("event_start", "player_id", "team", "market", "bookmaker", "line")
        key = tuple(str(row.get(x, "")).strip() for x in fields)
        if not all(key) or key in seen:
            errors.append(f"row {index}: missing or duplicate quote identity")
        seen.add(key)
        if status != "INVALID_LATE_CAPTURE":
            try:
                start = datetime.fromisoformat(row["event_start"].replace("Z", "+00:00"))
                captured = datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00"))
                if not (start.tzinfo and captured.tzinfo and captured < start):
                    errors.append(f"row {index}: quote not captured before tipoff")
                for field in ("original_projection", "combined_projection", "line", "side"):
                    if row.get(field) is None:
                        errors.append(f"row {index}: missing frozen {field}")
            except (KeyError, TypeError, AttributeError, ValueError):
                errors.append(f"row {index}: invalid pregame timestamp")
        if status == "SETTLED":
            if row.get("result") not in ("WIN", "LOSS", "PUSH") or row.get("actual") is None or not row.get("settlement_source"):
                errors.append(f"row {index}: incomplete final grade")
    if sampled:
        warnings.append("Only published sample inspected; full immutable ledger not verified")
        if not isinstance(data.get("captured"), int) or data["captured"] < len(records):
            errors.append("Captured summary smaller than published sample")
        if all(isinstance(data.get(k), int) for k in ("pending", "settled", "void_dnp", "captured")):
            if sum(data[k] for k in ("pending", "settled", "void_dnp")) != data["captured"]:
                errors.append("Published settlement counts do not add up")
    else:
        for field, expected in (("captured", len(records)), ("pending", counts["PENDING"]),
                                ("settled", counts["SETTLED"]), ("void_dnp", counts["VOID_DNP"])):
            if field in data and data[field] != expected:
                errors.append(f"{field}: summary={data[field]}, records={expected}")
    try:
        date = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
        if not date.tzinfo or (date-now).total_seconds() > 300:
            errors.append("Invalid/future generation time")
        elif (now-date).total_seconds() > 5400:
            warnings.append("Results are over 90 minutes old; check scheduled refresh")
    except (KeyError, AttributeError, ValueError, TypeError):
        errors.append("Invalid/missing generation time")
    if not records:
        warnings.append("No pregame quotes available to audit")
    return {"status": "FAIL" if errors else "WARN" if warnings else "PASS",
            "errors": errors[:50], "warnings": warnings,
            "counts": {"records": len(records), **counts},
            "live_prizepicks_verified": False, "live_tracker_verified": False,
            "replit_deployment_verified": False}


def main():
    path = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT / "docs/paper_results.json"
    try:
        result = audit(json.loads(path.read_text()))
    except (OSError, ValueError) as exc:
        result = {"status": "FAIL", "errors": [str(exc)], "warnings": []}
    print(json.dumps(result, indent=2))
    return int(result["status"] == "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())

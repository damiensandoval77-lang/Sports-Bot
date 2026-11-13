#!/usr/bin/env python3
"""Audit published Sports-Bot feed health without provider keys or external services."""
import argparse
import datetime as dt
import json
from pathlib import Path

UTC = dt.timezone.utc

def parse_timestamp(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except (ValueError, TypeError):
        return None

def assess(data, tracking, now=None, max_age_minutes=180):
    now = now or dt.datetime.now(UTC)
    findings = []
    def add(level, code, message):
        findings.append({"level": level, "code": code, "message": message})

    updated = parse_timestamp(data.get("updated_at"))
    if not updated:
        add("error", "ODDS_TIMESTAMP_MISSING", "Sportsbook feed has no valid updated_at")
    elif updated > now + dt.timedelta(minutes=5):
        add("error", "ODDS_TIMESTAMP_FUTURE", "Sportsbook observation is more than five minutes in the future")
    elif (now - updated).total_seconds() > max_age_minutes * 60:
        add("error", "ODDS_STALE", f"Sportsbook feed age: {int((now-updated).total_seconds()/60)} minutes")

    available = int(data.get("slate_events_available") or 0)
    checked = int(data.get("slate_events_checked") or 0)
    if available and checked == 0:
        add("error", "ZERO_SLATE_COVERAGE", f"{available} games available but none checked")
    elif available and checked < available:
        add("warning", "PARTIAL_SLATE_COVERAGE", f"Checked {checked} of {available} available games")

    if data.get("market_coverage_limited"):
        add("warning", "LIMITED_MARKETS", "Provider markets are limited")
    if data.get("picks") == [] and checked > 0:
        add("warning", "NO_PROVIDER_PICKS", "Checked games produced no eligible sportsbook picks")

    tracked = parse_timestamp(tracking.get("captured_at"))
    if not tracked:
        add("error", "TRACKER_TIMESTAMP_MISSING", "Live tracker missing valid captured_at")
    elif tracked > now + dt.timedelta(minutes=5):
        add("error", "TRACKER_TIMESTAMP_FUTURE", "Live observation is more than five minutes in the future")
    elif (now-tracked).total_seconds() > max_age_minutes * 60:
        add("warning", "TRACKER_STALE", "Live player observations have not updated recently")
    coverage = tracking.get("coverage") or {}
    missing = coverage.get("missing_fresh_matchups") or []
    if missing:
        add("error", "LIVE_MATCHUPS_MISSING", f"{len(missing)} active matchups lack fresh tracking")
    # When no games are active, an empty live games array is normal, not a failure.
    return {
        "checked_at": now.isoformat(),
        "ok": not any(f["level"] == "error" for f in findings),
        "sportsbook": {"updated_at": data.get("updated_at"), "slate_available": available, "slate_checked": checked},
        "live_tracker": {"captured_at": tracking.get("captured_at"), "active_matchups": len(coverage.get("active_matchups") or [])},
        "findings": findings,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--odds", default="docs/data.json")
    p.add_argument("--tracking", default="docs/live_player_tracking.json")
    p.add_argument("--max-age-minutes", type=int, default=180)
    p.add_argument("--output", default="")
    args = p.parse_args()
    data = json.loads(Path(args.odds).read_text())
    tracking = json.loads(Path(args.tracking).read_text())
    result = assess(data, tracking, max_age_minutes=args.max_age_minutes)
    print(json.dumps(result, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(0 if result["ok"] else 1)

if __name__ == "__main__":
    main()

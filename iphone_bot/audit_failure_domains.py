"""Credit-free, read-only reliability audit of committed Sports-Bot artifacts.

Never fetches odds, changes frozen picks, or tries to grade from unverified data.
"""
import datetime as dt
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "docs"

def load(relative):
    try:
        return json.loads((ROOT / relative).read_text())
    except (OSError, ValueError, UnicodeError) as exc:
        return {"_read_error": str(exc)}

def check_artifacts(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    reports = []
    def record(domain, level, code, detail):
        reports.append({"domain": domain, "level": level, "code": code, "detail": detail})

    grading = load("nfl/data/grading_health_2026.json")
    if grading.get("_read_error"):
        record("NFL grading", "critical", "HEALTH_UNAVAILABLE", grading["_read_error"])
    else:
        expected = grading.get("expected_final_picks")
        counted = sum(grading.get(k, 0) for k in ("graded_picks", "pending_picks", "void_picks"))
        if expected != counted:
            record("NFL grading", "critical", "SETTLEMENT_COUNT_MISMATCH",
                   f"expected={expected}, counted={counted}")
        elif grading.get("official_grading_scope") != "FROZEN_STANDARD_LINE_ONLY":
            record("NFL grading", "critical", "ALTERNATIVE_TIER_RISK", "Official grades must use standard lines only")
        else:
            record("NFL grading", "ok", "ACCOUNTED", f"{expected} final candidates accounted for")
        if grading.get("pending_picks", 0):
            record("NFL grading", "warning", "PENDING_FINAL_GRADES",
                   f"{grading['pending_picks']} pending frozen picks")

    readiness = load("production_readiness.json")
    if readiness.get("_read_error"):
        record("NBA readiness", "critical", "READINESS_REPORT_UNAVAILABLE", readiness["_read_error"])
    elif readiness.get("status") != "READY":
        record("NBA readiness", "critical", "PRODUCTION_NOT_READY",
               f"status={readiness.get('status')}; check published readiness blockers")
    else:
        record("NBA readiness", "ok", "READY", "Published readiness gate passed")

    join = load("ai_prizepicks_quick_join.json")
    if join.get("_read_error"):
        record("NBA lines and AI join", "critical", "JOIN_UNAVAILABLE", join["_read_error"])
    elif join.get("status") in ("STALE_OR_UNVERIFIED_SOURCE", "STALE_PROVIDER_BOARD", "ERROR"):
        record("NBA lines and AI join", "critical", "STALE_OR_UNVERIFIED_SOURCE",
               f"status={join.get('status')}; matched_games={join.get('matched_games')}")
    elif join.get("matched_games", 0) == 0:
        record("NBA lines and AI join", "warning", "ZERO_MATCHED_GAMES",
               "No fresh verified model-to-standard-line joins in saved output")
    else:
        record("NBA lines and AI join", "ok", "MATCHED",
               f"{join.get('matched_games')} verified matched games")

    capture = load("tonight_capture_gradeability.json")
    if capture.get("_read_error"):
        record("Pregame capture", "critical", "CAPTURE_REPORT_UNAVAILABLE", capture["_read_error"])
    elif capture.get("status") == "CAPTURE_INCOMPLETE":
        record("Pregame capture", "critical", "CAPTURE_INCOMPLETE",
               "At least one game has incomplete archived standard lines / forecasts")
    else:
        record("Pregame capture", "ok", "CAPTURE_STATUS",
               str(capture.get("status", "UNVERIFIED")))

    audit = load("ai_forecast_coverage_audit.json")
    if audit.get("_read_error"):
        record("NBA grading", "critical", "GRADE_AUDIT_UNAVAILABLE", audit["_read_error"])
    elif audit.get("status") == "VERIFIED_FINAL_ROWS_OUTSTANDING":
        record("NBA grading", "warning", "FINAL_ROWS_OUTSTANDING",
               "Frozen forecasts still require verified final reconciliation")
    else:
        record("NBA grading", "ok", "GRADE_AUDIT_STATUS", str(audit.get("status", "UNVERIFIED")))

    tracker = load("live_player_tracking.json")
    if tracker.get("_read_error"):
        record("NBA live tracking", "critical", "TRACKER_UNAVAILABLE", tracker["_read_error"])
    else:
        active = tracker.get("coverage", {}).get("active_matchups", [])
        missing = tracker.get("coverage", {}).get("missing_fresh_matchups", [])
        if missing:
            record("NBA live tracking", "critical", "ACTIVE_GAMES_UNTRACKED",
                   f"{len(missing)} active games lack fresh player observations")
        elif active and not tracker.get("games"):
            record("NBA live tracking", "critical", "NO_ACTIVE_PLAYER_DATA", "Active games but no live boxscores")
        else:
            record("NBA live tracking", "ok", "NO_MISSING_ACTIVE_GAMES",
                   f"{len(active)} active matchups at last published snapshot")

    return {"checked_at": now.isoformat(), "mode": "READ_ONLY_NO_PAID_APIS",
            "status": "DEGRADED" if any(x["level"] == "critical" for x in reports) else "OK",
            "checks": reports}

def main():
    report = check_artifacts()
    print(json.dumps(report, indent=2))
    summary = ["## Sports-Bot reliability audit", "",
               f"Status: **{report['status']}** — read-only; no provider credits used.", "",
               "| Domain | Severity | Finding |", "|---|---|---|"]
    for x in report["checks"]:
        summary.append(f"| {x['domain']} | {x['level'].upper()} | {x['code']}: {x['detail'].replace('|', '/')} |")
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a") as out:
            out.write("\n".join(summary) + "\n")
    return 1 if report["status"] == "DEGRADED" else 0

if __name__ == "__main__":
    raise SystemExit(main())

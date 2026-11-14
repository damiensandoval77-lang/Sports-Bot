"""Credit-free, read-only reliability audit of committed Sports-Bot artifacts.

Never fetches odds, changes frozen picks, or tries to grade from unverified data.
"""
import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent / "docs"

def load(relative):
    try:
        return json.loads((ROOT / relative).read_text())
    except (OSError, ValueError, UnicodeError) as exc:
        return {"_read_error": str(exc)}

def verified_posttip_slate(schedule,season,now):
    from iphone_bot.end_to_end_readiness import age_ok,parse_time
    from iphone_bot.season_schedule_baseline import validate
    try:
        validate(season)
        if schedule.get("coverage_complete") is not True or not age_ok(schedule.get("generated_at"),now,180):return False
        day=now.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        games=[g for g in schedule.get("games",[]) if g.get("date_eastern")==day]
        expected=[g for g in season["games"] if g["date_eastern"]==day]
        identity=lambda g:(g.get("away_abbreviation"),g.get("home_abbreviation"),g.get("start"))
        return bool(games) and len(games)==len(expected) and {identity(g) for g in games}=={identity(g) for g in expected} and all(parse_time(g.get("start")) and parse_time(g["start"])<=now for g in games)
    except (ValueError,KeyError,TypeError):
        return False

def grading_coverage_result(audit):
    """Accept only reconciled, explicit coverage evidence, never a status alone."""
    if not isinstance(audit, dict):
        return "critical", "GRADE_AUDIT_INVALID", "Coverage report must be an object"
    known = {"ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR", "VERIFIED_FINAL_ROWS_OUTSTANDING"}
    days = audit.get("days")
    if audit.get("status") not in known or not isinstance(days, dict) or not days:
        return "critical", "GRADE_AUDIT_INVALID", "Known status and nonempty daily coverage required"
    pending = 0
    captured_total = 0
    for day, row in days.items():
        try:
            if dt.date.fromisoformat(day).isoformat() != day or not isinstance(row, dict):
                raise ValueError
            keys = ("captured", "graded", "void_dnp", "excluded_nonparticipant", "pending", "accounted_for")
            if any(type(row.get(k)) is not int or row[k] < 0 for k in keys):
                raise ValueError
            resolved = row["graded"] + row["void_dnp"] + row["excluded_nonparticipant"]
            if row["accounted_for"] != resolved or row["captured"] != resolved + row["pending"]:
                raise ValueError
            by_game = row.get("pending_by_game")
            if (not isinstance(by_game, dict) or
                any(not isinstance(k, str) or not k.strip() or type(v) is not int or v <= 0
                    for k, v in by_game.items()) or sum(by_game.values()) != row["pending"]):
                raise ValueError
            pending += row["pending"]
            captured_total += row["captured"]
        except (ValueError, TypeError):
            return "critical", "GRADE_AUDIT_INVALID", "Daily grading counts or game backlog do not reconcile"
    if captured_total == 0:
        return "critical", "GRADE_AUDIT_INVALID", "No archived forecast coverage evidence"
    expected = "VERIFIED_FINAL_ROWS_OUTSTANDING" if pending else "ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR"
    if audit["status"] != expected:
        return "critical", "GRADE_AUDIT_INVALID", "Status contradicts reconciled pending count"
    if pending:
        return "warning", "FINAL_ROWS_OUTSTANDING", f"{pending} frozen forecasts still require verified final reconciliation"
    return "ok", "GRADE_AUDIT_STATUS", expected


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
            record("NFL grading", "ok", "ACCOUNTED", f"{expected} historical final candidates accounted for across all tiers")
        # The legacy totals include alternative tiers. Only explicit standard
        # counts describe the official board; absent data must not imply zero.
        pending = grading.get("standard_pending_picks")
        if type(pending) is not int or pending < 0:
            record("NFL grading", "critical", "STANDARD_PENDING_COUNT_INVALID",
                   "Explicit nonnegative standard-line pending count required")
        elif pending:
            record("NFL grading", "warning", "PENDING_FINAL_GRADES",
                   f"{pending} pending frozen standard-line picks")
        else:
            record("NFL grading", "ok", "STANDARD_GRADES_SETTLED",
                   "0 pending frozen standard-line picks")
        record("NFL grading archive", "ok", "ALTERNATIVE_TIERS_EXCLUDED",
               f"{grading.get('alternative_tier_historical_grades_excluded', 'unknown')} "
               "historical alternative-tier grades and "
               f"{grading.get('alternative_tier_pending_excluded', 'unknown')} "
               "pending alternative-tier rows excluded from official standard results")

    def freshness(domain, report, field, max_age_minutes):
        raw = report.get(field)
        if not raw:
            record(domain, "warning", "MISSING_HEALTH_TIMESTAMP", f"Missing {field}; health report freshness unverified")
            return
        try:
            stamped = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if stamped.tzinfo is None:
                raise ValueError("timezone missing")
            age = (now - stamped).total_seconds() / 60
        except (ValueError, TypeError):
            record(domain, "warning", "BAD_HEALTH_TIMESTAMP", f"Invalid {field}={raw}")
            return
        if age > max_age_minutes or age < -5:
            record(domain, "warning", "STALE_HEALTH_REPORT",
                   f"{field} aged {age:.0f} minutes; maximum {max_age_minutes}")

    horizon = load("nba_schedule_horizon_audit.json")
    if horizon.get("status") != "READY":
        record("NBA full-season schedule", "critical", "MISSING_PUBLISHED_FIXTURES",
               f"14-day fixture coverage status={horizon.get('status')}; reasons={horizon.get('reason_codes',[])}")
    elif horizon.get("season_fixed_games", 0) < 900:
        record("NBA full-season schedule", "critical", "SHORT_SEASON_ARCHIVE",
               "The published season archive contains too few games")
    else:
        record("NBA full-season schedule", "ok", "NEXT_14_DAYS_ACCOUNTED",
               f"{horizon['season_fixed_games']} fixed released fixtures saved and next two days reconciled")
    freshness("NBA full-season schedule", horizon, "checked_at", 480)

    readiness = load("production_readiness.json")
    freshness("NBA readiness", readiness, "checked_at", 120)
    if readiness.get("_read_error"):
        record("NBA readiness", "critical", "READINESS_REPORT_UNAVAILABLE", readiness["_read_error"])
    elif readiness.get("status") != "READY":
        record("NBA readiness", "critical", "PRODUCTION_NOT_READY",
               f"status={readiness.get('status')}; check published readiness blockers")
    else:
        record("NBA readiness", "ok", "READY", "Published readiness gate passed")

    join = load("ai_prizepicks_quick_join.json")
    freshness("NBA lines and AI join", join, "generated_at", 120)
    if join.get("_read_error"):
        record("NBA lines and AI join", "critical", "JOIN_UNAVAILABLE", join["_read_error"])
    elif join.get("status")!="ERROR" and verified_posttip_slate(load("nba_schedule.json"),load("nba_season_schedule_2026_27.json"),now):
        record("NBA lines and AI join", "ok", "POSTTIP_USE_IMMUTABLE_CAPTURES",
               "All independently scheduled games have tipped; capture integrity is checked separately below")
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
    freshness("Pregame capture", capture, "checked_at", 180)
    if capture.get("_read_error"):
        record("Pregame capture", "critical", "CAPTURE_REPORT_UNAVAILABLE", capture["_read_error"])
    elif capture.get("status") == "CAPTURE_INCOMPLETE":
        summary = capture.get("summary", {})
        missing = summary.get("total_standard_markets_without_frozen_model")
        fallback = summary.get("total_missing_primary_with_separate_research_receipt")
        unrecovered = summary.get("total_missing_primary_without_any_ai_receipt")
        if all(type(v) is int and v >= 0 for v in (missing, fallback, unrecovered)):
            if missing != fallback + unrecovered:
                record("Pregame capture", "critical", "CAPTURE_MATH_INCONSISTENT",
                       f"unmatched={missing}, research_fallback={fallback}, no_ai_receipt={unrecovered}")
            record("Pregame capture", "critical", "PRIMARY_FROZEN_MODEL_INCOMPLETE",
                   f"{missing} exact standard prices lack primary frozen models; "
                   f"{fallback} have independently preserved research receipts, "
                   f"{unrecovered} have no AI receipt")
        else:
            record("Pregame capture", "critical", "CAPTURE_INCOMPLETE",
                   "Saved quote and model coverage incomplete or missing exact reconciliation counts")
    else:
        record("Pregame capture", "ok", "CAPTURE_STATUS",
               str(capture.get("status", "UNVERIFIED")))

    receipt = load("standard_quote_ai_research_archive.json")
    if receipt.get("status") != "IMMUTABLE_PRETIP_STANDARD_QUOTE_AI_RESEARCH":
        record("Research archive", "critical", "RECEIPT_ARCHIVE_UNAVAILABLE",
               "Credit-free standard-line research receipts missing or invalid")
    elif receipt.get("count") != len(receipt.get("records", [])):
        record("Research archive", "critical", "RECEIPT_COUNT_MISMATCH",
               "Archived standard quote-AI receipt count does not match rows")
    else:
        record("Research archive", "ok", "RECEIPTS_RETAINED",
               f"{receipt.get('count')} separate historical research receipts (not official grades)")

    audit = load("ai_forecast_coverage_audit.json")
    freshness("NBA grading", audit, "checked_at", 240)
    if audit.get("_read_error"):
        record("NBA grading", "critical", "GRADE_AUDIT_UNAVAILABLE", audit["_read_error"])
    else:
        record("NBA grading", *grading_coverage_result(audit))

    provider = load("prizepicks_site.json")
    if provider.get("status") != "LIVE_THIRD_PARTY_PRIZEPICKS_LINES":
        record("PrizePicks provider", "critical", "NO_VERIFIED_SOURCE", str(provider.get("status")))
    elif provider.get("partial_board") is True or provider.get("complete_provider_board") is not True:
        record("PrizePicks provider", "warning", "PARTIAL_PROVIDER_COVERAGE",
               "Some upcoming standard offers may be missing despite valid captured quotes")
    else:
        record("PrizePicks provider", "ok", "COMPLETE_SOURCE", "Provider board reports complete coverage")

    tracker = load("live_player_tracking.json")
    freshness("NBA live tracking", tracker, "captured_at", 120)
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

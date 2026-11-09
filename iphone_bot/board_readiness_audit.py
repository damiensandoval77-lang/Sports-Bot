#!/usr/bin/env python3
"""Read-only Phase 1 board readiness audit; never calls paid APIs."""
import argparse
import datetime as dt
import json
from pathlib import Path

UTC = dt.timezone.utc

def timestamp(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except ValueError:
        return None

def inspect(odds, projections, paper, now=None, max_age_minutes=180):
    now = now or dt.datetime.now(UTC)
    checks = []
    def record(code, passed, detail):
        checks.append({"code": code, "passed": bool(passed), "detail": detail})

    available = odds.get("slate_events_available", 0)
    checked = odds.get("slate_events_checked", 0)
    if not isinstance(available, int) or not isinstance(checked, int) or available < 0 or checked < 0:
        record("VALID_GAME_COUNTS", False, "Game counts must be nonnegative integers")
        available, checked = 0, 0
    else:
        record("VALID_GAME_COUNTS", checked <= available or available == 0, f"available={available}; checked={checked}")
    odds_at = timestamp(odds.get("updated_at"))
    odds_fresh = bool(odds_at and 0 <= (now-odds_at).total_seconds() <= max_age_minutes*60)
    record("FRESH_BOOK_LINES", odds_fresh, f"last_updated={odds.get('updated_at') or 'missing'}")
    if available:
        record("GAME_COVERAGE", checked == available, f"{checked}/{available} checked")
    else:
        record("GAME_COVERAGE", True, "No available games reported; cannot infer full slate independently")

    # Research status is not proof of a current actionable pregame board.
    status = projections.get("status")
    generated_at = timestamp(projections.get("generated_at"))
    fresh_proj = bool(generated_at and 0 <= (now-generated_at).total_seconds() <= max_age_minutes*60)
    is_board = bool(projections.get("fresh_pregame_board") is True and
                    isinstance(projections.get("fresh_board_games"), list) and
                    projections.get("fresh_board_games"))
    record("FRESH_PREGAME_BOARD", fresh_proj and is_board,
           f"status={status!r}; fresh_board_flag={projections.get('fresh_pregame_board')!r}; "
           "research-only timestamps do not establish playable projections")
    record("LINE_SOURCE_LABELED", bool(odds.get("disclaimer") or odds.get("line_source")),
           "Users must distinguish sportsbook lines from PrizePicks")
    paper_at = timestamp(paper.get("generated_at"))
    paper_counts = [paper.get("captured"), paper.get("settled"), paper.get("pending"), paper.get("void_dnp")]
    valid_counts = all(isinstance(v, int) and v >= 0 for v in paper_counts)
    counts_match = valid_counts and paper_counts[0] == sum(paper_counts[1:])
    record("PAPER_GRADE_TOTALS", counts_match,
           f"captured={paper.get('captured')}; settled={paper.get('settled')}; "
           f"pending={paper.get('pending')}; void={paper.get('void_dnp')}")
    record("PAPER_REPORT_TIMESTAMP", bool(paper_at and paper_at <= now),
           f"generated_at={paper.get('generated_at')!r}; this checks report validity, NOT grading timeliness")
    return {"checked_at": now.isoformat(), "ready": all(x["passed"] for x in checks),
            "checks": checks, "note": "This audits committed snapshots only, not live API availability or runtime scheduling."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--odds", default="docs/data.json")
    p.add_argument("--projections", default="docs/projection_upgrade_status.json")
    p.add_argument("--paper", default="docs/paper_results.json")
    p.add_argument("--max-age-minutes", type=int, default=180)
    p.add_argument("--fail-on-unready", action="store_true")
    a=p.parse_args()
    obj=inspect(json.loads(Path(a.odds).read_text()),
                json.loads(Path(a.projections).read_text()),
                json.loads(Path(a.paper).read_text()),
                max_age_minutes=a.max_age_minutes)
    print(json.dumps(obj,indent=2))
    if a.fail_on_unready and not obj["ready"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()

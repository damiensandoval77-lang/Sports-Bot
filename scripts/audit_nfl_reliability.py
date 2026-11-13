"""Read-only NFL pipeline consistency gate; never changes or fabricates picks."""
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from reconcile_nfl_picks import closing

ROOT = Path("docs/nfl/data")


def rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def audit(root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    root = Path(root)
    problems, warnings = [], []
    def load(path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{path.name}: unreadable or missing ({type(exc).__name__})")
            return {}

    schedule = load(root / "schedule_2026.json")
    games = schedule.get("games", [])
    ids = [g.get("game_id") for g in games]
    if schedule.get("game_count") != 272 or len(games) != 272 or len(set(ids)) != 272:
        problems.append("season schedule missing or duplicated games")
    finals = {g.get("game_id") for g in games if g.get("status") == "final"}

    snapshot = load(root / "latest_2026.json")
    chunks = snapshot.get("files", [])
    if not chunks or len(chunks) > 40 or len(set(chunks)) != len(chunks):
        problems.append("snapshot manifest missing or duplicate chunk references")
    total = 0
    for name in chunks:
        if not isinstance(name, str) or not name.startswith("latest_2026_") or not name.endswith(".csv") or "/" in name or "\\" in name:
            problems.append("snapshot manifest references unsafe chunk")
            continue
        path = root / name
        try:
            data = rows(path)
            total += len(data)
            if any(r.get("captured_at") != snapshot.get("captured_at") for r in data):
                problems.append(f"{name}: mixed capture timestamps")
        except (OSError, UnicodeError, csv.Error):
            problems.append(f"{name}: unreadable chunk")
    if not isinstance(snapshot.get("rows"), int) or total != snapshot.get("rows") or total < 5:
        problems.append("snapshot manifest row count disagrees with available chunks")

    # Freshness is operational health, independent of CSV structural validity.
    # Warn ahead of upcoming kickoffs and fail only when a capture is severely
    # stale close to kickoff. No new rows are invented to make a run pass.
    captured = snapshot.get("captured_at")
    capture_age_hours = None
    try:
        stamp = datetime.fromisoformat(str(captured).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("naive timestamp")
        capture_age_hours = round((now - stamp.astimezone(timezone.utc)).total_seconds() / 3600, 2)
        if capture_age_hours < -0.25:
            problems.append("NFL snapshot timestamp is unexpectedly in the future")
    except (ValueError, TypeError, OverflowError):
        problems.append("NFL snapshot capture timestamp is invalid")
    upcoming_hours = []
    for game in games:
        if game.get("status") == "final":
            continue
        try:
            kickoff = datetime.fromisoformat(str(game.get("kickoff_utc")).replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                continue
            delta = (kickoff.astimezone(timezone.utc) - now).total_seconds() / 3600
            if 0 <= delta <= 24:
                upcoming_hours.append(delta)
        except (ValueError, TypeError, OverflowError):
            continue
    nearest_kickoff_hours = round(min(upcoming_hours), 2) if upcoming_hours else None
    if capture_age_hours is not None and upcoming_hours:
        if capture_age_hours > 36 and min(upcoming_hours) <= 4:
            problems.append("NFL capture older than 36 hours within 4 hours of kickoff")
        elif capture_age_hours > 12:
            warnings.append("NFL capture older than 12 hours with a game in the next 24 hours")

    health = load(root / "grading_health_2026.json")
    try:
        archive = rows(root / "frozen_pick_history_2026.csv")
        graded = rows(root / "pp_graded_2026.csv")
        pending = rows(root / "pp_grading_pending_2026.csv")
    except (OSError, UnicodeError, csv.Error) as exc:
        problems.append(f"grading CSV unavailable: {type(exc).__name__}")
        archive, graded, pending = [], [], []
    counts = {
        "archived_pregame_lines": len(archive),
        "graded_picks": sum(r.get("grade_status") == "graded" for r in graded),
        "pending_picks": len(pending),
        "expected_final_picks": len(graded) + len(pending),
    }
    for key, actual in counts.items():
        if health.get(key) != actual:
            problems.append(f"grading health {key}={health.get(key)} disagrees with CSV count={actual}")
    void_count = sum(r.get("grade_status") == "void_verified_inactive" for r in graded)
    if health.get("void_picks", 0) != void_count:
        problems.append("grading health void_picks disagrees with verified inactive CSV count")
    if any(r.get("grade_status") == "void_verified_inactive" and
           (r.get("actual") not in (None, "") or r.get("result") != "Void" or
            r.get("won") not in (None, "")) for r in graded):
        problems.append("verified inactive void has a fabricated actual or win/loss")
    # Independently derive which pre-kickoff frozen quotes should be represented
    # in the grading ledger. A successful job must not silently drop eligible picks.
    finished = {g.get("game_id") for g in games if g.get("status") == "final"
                and g.get("home_score") is not None and g.get("away_score") is not None}
    eligible = closing(archive, finished)
    def grade_key(r):
        return tuple(str(r.get(field, "")) for field in
                     ("game_id", "player_id", "target", "odds_type", "line"))
    expected_keys = {grade_key(r) for r in eligible}
    actual_keys = [grade_key(r) for r in graded + pending]
    if len(actual_keys) != len(set(actual_keys)):
        problems.append("duplicate rows in final pick grading ledger")
    missing = expected_keys - set(actual_keys)
    extras = set(actual_keys) - expected_keys
    if missing:
        problems.append(f"{len(missing)} eligible frozen final picks absent from grading ledger")
    if extras:
        problems.append(f"{len(extras)} ledger picks have no eligible frozen final quote")
    for r in graded + pending:
        if r.get("game_id") not in finals:
            problems.append("grading ledger includes game not marked final")
            break
    if any(r.get("grade_status") not in ("graded", "void_verified_inactive") for r in graded):
        problems.append("graded CSV contains ungraded entries")
    if any(r.get("grade_status") in ("graded", "void_verified_inactive") for r in pending):
        problems.append("pending CSV contains graded entries")

    box = load(root / "boxscores" / "manifest.json")
    if box.get("season") != 2026 or box.get("games_with_stats", 0) > len(finals):
        problems.append("box-score manifest inconsistent with completed season schedule")
    if len(graded) == 0:
        warnings.append("no graded picks yet; this is not a failure unless valid pre-kickoff picks reached finals")

    status = "FAILED" if problems else "HEALTHY"
    report = {
        "status": status,
        "scheduled_games": len(games),
        "final_games": len(finals),
        "boxscore_games": box.get("games_with_stats", 0),
        "snapshot_rows": total,
        "snapshot_age_hours": capture_age_hours,
        "nearest_kickoff_hours": nearest_kickoff_hours,
        "archived_pregame_lines": len(archive),
        "graded_picks": counts["graded_picks"],
        "void_picks": void_count,
        "pending_picks": len(pending),
        "eligible_frozen_final_picks": len(expected_keys),
        "missing_final_pick_grades": len(missing),
        "warnings": warnings,
        "problems": problems,
    }
    return report


def main():
    report = audit()
    rendered = json.dumps(report, indent=2)
    print("NFL reliability audit:", rendered)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("### NFL data reliability audit\n\n\x60\x60\x60json\n" + rendered + "\n\x60\x60\x60\n")
    if report["problems"]:
        raise SystemExit("NFL pipeline data inconsistency detected; do not claim fully healthy grading")


if __name__ == "__main__":
    main()

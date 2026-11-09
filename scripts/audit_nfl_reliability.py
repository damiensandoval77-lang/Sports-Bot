"""Read-only NFL pipeline consistency gate; never changes or fabricates picks."""
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("docs/nfl/data")


def rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def audit(root=ROOT):
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
        "graded_picks": len(graded),
        "pending_picks": len(pending),
        "expected_final_picks": len(graded) + len(pending),
    }
    for key, actual in counts.items():
        if health.get(key) != actual:
            problems.append(f"grading health {key}={health.get(key)} disagrees with CSV count={actual}")
    for r in graded + pending:
        if r.get("game_id") not in finals:
            problems.append("grading ledger includes game not marked final")
            break
    if any(r.get("grade_status") != "graded" for r in graded):
        problems.append("graded CSV contains ungraded entries")
    if any(r.get("grade_status") == "graded" for r in pending):
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
        "archived_pregame_lines": len(archive),
        "graded_picks": len(graded),
        "pending_picks": len(pending),
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

"""Attempt each independent free recovery, retaining failures as evidence.

Public health JSON may select only this explicit no-provider-credit allowlist.
An unavailable run inventory is not permission to dispatch a duplicate job.
"""
import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

FREE_WORKFLOWS = frozenset({
    "nba-prizepicks-site-publish.yml", "nba-new-ai-all-markets.yml",
    "independent_scoreboard_refresh.yml", "independent_nba_player_boxscores.yml",
    "nba-new-ai-multimarket-grade.yml", "nba-prizepicks-research-ledger.yml",
    "grade_frozen_ai_forecasts.yml",
})
ACTIVE = {"queued", "pending", "waiting", "requested", "in_progress"}


def gh(args):
    result = subprocess.run(["gh", *args], text=True, capture_output=True, timeout=45)
    if result.returncode:
        # Do not persist CLI stderr: it can contain credentials or response bodies.
        raise RuntimeError("GH_COMMAND_FAILED")
    return result.stdout


def recover(report, *, now=None, command=gh):
    now = now or dt.datetime.now(dt.timezone.utc)
    results = []
    workflows = sorted({str(row["recovery_workflow"])
                        for row in report["stages"]
                        if row.get("status") == "FAIL" and row.get("recovery_workflow")})
    for workflow in workflows:
        item = {"workflow": workflow}
        results.append(item)
        if workflow not in FREE_WORKFLOWS:
            item.update(status="BLOCKED", reason="NOT_ALLOWLISTED_FREE_WORKFLOW")
            continue
        try:
            runs = json.loads(command(["run", "list", "--workflow", workflow,
                                      "--limit", "30", "--json",
                                      "createdAt,updatedAt,status,conclusion,headBranch"]))
            if not isinstance(runs, list):
                raise ValueError("INVALID_RUN_INVENTORY")
            busy = False
            for run in runs:
                if run.get("headBranch") != "main":
                    continue
                if run.get("status") in ACTIVE:
                    busy = True
                    continue
                if run.get("status") != "completed":
                    raise ValueError("UNKNOWN_RUN_STATUS")
                failed = run.get("conclusion") != "success"
                timestamp = run["updatedAt"] if failed else run["createdAt"]
                created = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if created.tzinfo is None or created > now:
                    raise ValueError("INVALID_RUN_TIMESTAMP")
                # Completion-triggered failures need a backoff too. Otherwise
                # this independent heartbeat can bypass the readiness gate.
                backoff = (900 if workflow == "nba-new-ai-all-markets.yml" else 300) if failed else 1800
                busy |= (now - created).total_seconds() <= backoff
            if busy:
                item.update(status="SKIPPED", reason="ACTIVE_RECENT_SUCCESS_OR_FAILURE_BACKOFF")
                continue
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError,
                OSError, subprocess.SubprocessError) as exc:
            item.update(status="BLOCKED", reason="RUN_INVENTORY_UNAVAILABLE", error_type=type(exc).__name__)
            continue
        try:
            command(["workflow", "run", workflow, "--ref", "main"])
            item.update(status="DISPATCHED")
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            item.update(status="FAILED", reason="DISPATCH_FAILED", error_type=type(exc).__name__)
    return {"checked_at": now.isoformat(), "recoveries": results,
            "status": "INCOMPLETE" if any(x["status"] in {"FAILED", "BLOCKED"} for x in results) else "COMPLETE",
            "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = recover(json.loads(args.report.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return int(result["status"] != "COMPLETE")


if __name__ == "__main__":
    raise SystemExit(main())

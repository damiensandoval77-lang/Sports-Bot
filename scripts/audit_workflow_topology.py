"""Read-only GitHub Actions topology inventory for the reliability migration.

Static text heuristics identify shared cron, groups, and candidate multiwriters.
No data writes, provider calls, or claimed successful dispatches.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

WATCHED = (
    "docs/lagged_matchup_all_market_ledger.json",
    "docs/ai_forecast_actual_ledger.json",
    "docs/nba_player_tracking_independent.json",
    "docs/nba_scoreboard_independent.json",
    "docs/nba_schedule.json",
    "docs/prizepicks.json",
    "docs/prizepicks_site.json",
    "docs/dames-picks/published_pick_settlement.json",
)
CONCURRENCY = re.compile(r"^\s*group:\s*['\"]?([^#\n'\"]+)", re.MULTILINE)
CRON = re.compile(r"^\s*-?\s*cron:\s*['\"]?([^#\n'\"]+)", re.MULTILINE)
WRITE = re.compile(r"^\s*contents:\s*write\s*$", re.MULTILINE)
COMMIT = re.compile(r"\bgit\s+(?:commit|push|add)\b")


def audit(workflow_dir):
    root = Path(workflow_dir)
    jobs = []
    for path in sorted([*root.glob("*.yml"), *root.glob("*.yaml")]):
        source = path.read_text(encoding="utf-8")
        groups = sorted(set(x.strip() for x in CONCURRENCY.findall(source)))
        schedules = [x.strip() for x in CRON.findall(source)]
        can_write = bool(WRITE.search(source))
        commits = bool(COMMIT.search(source))
        writes = []
        if can_write and commits:
            for target in WATCHED:
                escaped = re.escape(target)
                if re.search(r"\bgit\s+add\b[^\n]*"+escaped, source) or (
                    re.search(r"\bmerge_[\w]+\b[^\n]*"+escaped, source) and
                    re.search(r"\bgit\s+add\b", source)
                ):
                    writes.append(target)
        jobs.append({
            "workflow": path.name,
            "cron_triggers": len(schedules),
            "concurrency_groups": groups,
            "writes_to_main_possible": can_write and commits,
            "tracked_published_targets": sorted(writes),
        })
    groups = defaultdict(list)
    writers = defaultdict(list)
    for job in jobs:
        for group in job["concurrency_groups"]:
            if "${{" not in group:
                groups[group].append(job["workflow"])
        for target in job["tracked_published_targets"]:
            writers[target].append(job["workflow"])
    return {
        "scope": "STATIC_WORKFLOW_TOPOLOGY_READ_ONLY_HEURISTIC",
        "workflow_files": len(jobs),
        "scheduled_workflows": sum(bool(j["cron_triggers"]) for j in jobs),
        "scheduled_cron_entries": sum(j["cron_triggers"] for j in jobs),
        "workflows_with_possible_git_writes": sum(j["writes_to_main_possible"] for j in jobs),
        "shared_literal_concurrency_groups": {
            k: v for k, v in sorted(groups.items()) if len(v) > 1
        },
        "watched_multiwriter_targets": {
            k: v for k, v in sorted(writers.items()) if len(v) > 1
        },
        "watched_writer_inventory": dict(sorted(writers.items())),
        "limitations": [
            "Text-based heuristic, not an Actions run log or complete GitHub YAML parser",
            "May miss writes performed inside scripts or dynamic git add expressions",
            "Does not prove dispatch frequency, successful pushes, or cancellation rate",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflows", default=".github/workflows")
    args = parser.parse_args()
    print(json.dumps(audit(args.workflows), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

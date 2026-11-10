"""Deterministic recovery routing for a degraded NBA readiness report.

No provider calls, mutations, or wagering here. GitHub workflow owns bounded dispatch.
A failed/degraded report remains failed until the next independent verification.
"""
import json
import sys
from pathlib import Path

RECOVERABLE = {
    "prizepicks_lines": "nba-prizepicks-full-slate.yml",
    "pregame_capture": "nba-tonight-capture-gradeability.yml",
    "public_browser": "nba-prizepicks-site-publish.yml",
}
NO_COST = ("nba-prizepicks-site-publish.yml", "nba-tonight-capture-gradeability.yml")

def recovery_targets(report):
    if report.get("status") == "READY":
        return []
    components = report.get("components")
    if not isinstance(components, dict):
        return []
    failed = {key for key, value in components.items()
              if isinstance(value, dict) and value.get("required") is True
              and value.get("state") != "READY"}
    out = []
    if "prizepicks_lines" in failed and report.get("upcoming_games", 0) > 0:
        out.append(RECOVERABLE["prizepicks_lines"])
    if "public_browser" in failed:
        out.append(RECOVERABLE["public_browser"])
    if "pregame_capture" in failed:
        out.append(RECOVERABLE["pregame_capture"])
    return out

def main():
    report = json.loads(Path(sys.argv[1]).read_text())
    for workflow in recovery_targets(report):
        print(workflow)

if __name__ == "__main__":
    main()

"""Deterministic recovery routing for a degraded NBA readiness report.

No provider calls, mutations, or wagering here. GitHub workflow owns bounded dispatch.
A failed/degraded report remains failed until the next independent verification.
"""
import json
import sys
from pathlib import Path

RECOVERABLE = {
    "prizepicks_lines": "nba-prizepicks-full-slate.yml",
    "pregame_capture": "nba-new-ai-all-markets.yml",
    "public_browser": "nba-prizepicks-site-publish.yml",
    "scoreboard": "independent_scoreboard_refresh.yml",
    "live_player_stats": "independent_nba_player_boxscores.yml",
}
NO_COST = ("nba-prizepicks-site-publish.yml", "nba-new-ai-all-markets.yml",
           "independent_scoreboard_refresh.yml", "independent_nba_player_boxscores.yml",
           "nba-live-tracker-backup.yml")

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
    # Never leave an in-progress game waiting for a user to refresh the live
    # feeds. These free source collectors preserve only verified observations.
    if "scoreboard" in failed:
        out.append(RECOVERABLE["scoreboard"])
    if "live_player_stats" in failed:
        out.append(RECOVERABLE["live_player_stats"])
        # An official-feed outage needs an independent verified fallback, not
        # repeated retries against only the same unavailable provider.
        out.append("nba-live-tracker-backup.yml")
    # Rerunning a capture audit cannot repair absent frozen projections.
    # Route pretip gaps to model generation and verify in the next audit.
    if "pregame_capture" in failed and report.get("upcoming_games", 0) > 0:
        out.append(RECOVERABLE["pregame_capture"])
    return out

def main():
    report = json.loads(Path(sys.argv[1]).read_text())
    for workflow in recovery_targets(report):
        print(workflow)

if __name__ == "__main__":
    main()

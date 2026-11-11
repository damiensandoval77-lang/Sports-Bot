"""Capture real, timestamped NBA matchup evidence for research, never live picks.

Only sourced fields from current_form, schedule and official injury context.
Observed minutes != projected minutes; unknown teammate/injury data != healthy.
This module does NOT invent position-defense, usage, depth, pace or an estimate.
"""
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

FACTORS = ("opponent_position_defense", "projected_minutes",
           "usage_opportunities", "teammate_availability", "depth_role",
           "pace_possessions")


def when(s):
    try:
        if not isinstance(s, str):
            return None
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except ValueError:
        return None


def good_number(x):
    return type(x) in (int, float) and 0 < x < float("inf")


def capture(form, schedule, injury, *, frozen_at):
    frozen = when(frozen_at)
    ft, st, it = (when(form.get("updated_at")),
                  when(schedule.get("generated_at")),
                  when(injury.get("report_issued_at")))
    if not frozen or not ft or not st or ft > frozen or st > frozen:
        raise ValueError("Form and schedule must be sourced before snapshot capture")
    if not form.get("source_url") or not schedule.get("source_url"):
        raise ValueError("Original source URLs required")
    if not isinstance(form.get("players"), list) or not isinstance(schedule.get("games"), list):
        raise ValueError("Source player and fixture records missing")
    if injury.get("injury_data_verified") is not True or not it or it > frozen:
        raise ValueError("Verified, pre-capture official injury report required")
    if not injury.get("source_pdf"):
        raise ValueError("Official injury source URL missing")

    by_team = defaultdict(list)
    for p in form["players"]:
        if not isinstance(p, dict) or not p.get("player_id") or not p.get("team"):
            continue
        by_team[p["team"]].append(p)

    injury_idx = defaultdict(list)
    for p in injury.get("players", []):
        if isinstance(p, dict):
            key = (str(p.get("player_id")), p.get("team"), p.get("game_date"))
            injury_idx[key].append(p.get("status"))

    records = []
    games = []
    blockers = Counter()
    for g in schedule["games"]:
        tip = when(g.get("start"))
        day = g.get("date_eastern")
        home, away = g.get("home_abbreviation"), g.get("away_abbreviation")
        if not tip or not day or not home or not away or tip <= frozen:
            continue
        if home == away or not g.get("id"):
            raise ValueError("Invalid scheduled matchup identity")
        games.append({"game_id": g["id"], "start": g["start"], "date_eastern": day,
                      "home": home, "away": away})
        for team, opponent in ((home, away), (away, home)):
            for p in by_team[team]:
                # Ensure exactly one roster identity for the player on this team.
                candidates = by_team[team]
                if sum(str(x.get("player_id")) == str(p["player_id"]) for x in candidates) != 1:
                    blockers["duplicate_player_team_identity"] += 1
                    continue
                latest_game = p.get("latest_game")
                if not latest_game or latest_game >= day:
                    blockers["missing_or_postmatch_player_games"] += 1
                    continue
                fields = form.get("log_fields", [])
                logs = p.get("log", [])
                if not isinstance(fields, list) or "date" not in fields or "MIN" not in fields:
                    blockers["missing_game_log_schema"] += 1
                    continue
                date_idx, min_idx = fields.index("date"), fields.index("MIN")
                if not isinstance(logs, list) or any(
                    not isinstance(entry, list) or len(entry) <= max(date_idx, min_idx) or
                    not isinstance(entry[date_idx], str) or entry[date_idx] >= day
                    for entry in logs):
                    blockers["unsafe_or_invalid_game_logs"] += 1
                    continue
                minute_values = [entry[min_idx] for entry in logs if good_number(entry[min_idx])]
                if len(minute_values) < 3:
                    blockers["insufficient_observed_minutes"] += 1
                    continue
                statuses = injury_idx[(str(p["player_id"]), team, day)]
                injury_status = statuses[0] if len(set(statuses)) == 1 and statuses else None
                if len(set(statuses)) > 1:
                    blockers["conflicting_official_injury_status"] += 1
                    continue
                if injury_status is None:
                    blockers["unlisted_injury_status_unknown"] += 1
                # Record the real observed baseline, never call it projected playing time.
                records.append({
                    "game_id": g["id"], "start": g["start"], "date_eastern": day,
                    "player_id": str(p["player_id"]), "player": p.get("player"),
                    "team": team, "opponent": opponent,
                    "observed_minutes_last3": round(sum(minute_values[-3:]) / 3, 2),
                    "observed_minutes_count": len(minute_values),
                    "last_observed_game_date": latest_game,
                    "minutes_source": form["source_url"],
                    "minutes_source_published_at": form["updated_at"],
                    "injury_status": injury_status or "UNKNOWN_NOT_LISTED",
                    "injury_source": injury["source_pdf"] if injury_status is not None else None,
                    "injury_report_issued_at": injury.get("report_issued_at") if injury_status is not None else None,
                    "unknown_required_matchup_inputs": list(FACTORS),
                    "eligible_for_hit_estimate": False,
                })
    ids = [(x["game_id"], x["player_id"], x["team"]) for x in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Nonunique player/game IDs")
    return {
        "status": "SOURCE_LINKED_PREGAME_RESEARCH_ONLY",
        "captured_at": frozen_at,
        "production_hit_estimate_eligible": False,
        "provider_api_calls": 0,
        "source_timestamps": {
            "player_form": form["updated_at"],
            "schedule": schedule["generated_at"],
            "official_injury_report": injury["report_issued_at"],
        },
        "future_games": games, "research_players": records,
        "future_game_count": len(games), "research_player_count": len(records),
        "missing_feature_reasons": dict(sorted(blockers.items())),
        "not_yet_available": list(FACTORS),
        "note": ("Observed past-minute averages and verified dated injury statuses are "
                 "context only, NOT a projected minutes model, teammate split, "
                 "opponent position-defense, or calibrated hit probability. "
                 "No historical prediction is backfilled."),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--form", default="docs/current_form.json")
    parser.add_argument("--schedule", default="docs/nba_schedule.json")
    parser.add_argument("--injury", default="docs/injury_context.json")
    parser.add_argument("--frozen-at")
    parser.add_argument("--output", default="pregame-evidence-research.json")
    a = parser.parse_args()
    clock = a.frozen_at or datetime.now(timezone.utc).isoformat()
    report = capture(json.loads(Path(a.form).read_text()),
                     json.loads(Path(a.schedule).read_text()),
                     json.loads(Path(a.injury).read_text()), frozen_at=clock)
    Path(a.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in (
        "status", "captured_at", "future_game_count", "research_player_count",
        "production_hit_estimate_eligible", "missing_feature_reasons")}, indent=2))


if __name__ == "__main__":
    main()

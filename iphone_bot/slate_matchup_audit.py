#!/usr/bin/env python3
"""Compare the independent Eastern-day NBA slate with published sportsbook coverage.

Read-only, no API keys or paid requests. A missing matchup is NOT a missing
book line if a provider has no market, but must not be silently hidden.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")

def normalize_game(value):
    return " ".join(str(value or "").casefold().strip().split())

def coverage(schedule, odds, eastern_day):
    games = [g for g in schedule.get("games", [])
             if g.get("date_eastern") == eastern_day and g.get("game_state") != "post"]
    unique = {normalize_game(g.get("game")): g for g in games if g.get("game")}
    entries = list(odds.get("events_covered") or [])
    covered = set()
    for event in entries:
        if isinstance(event, dict):
            game = normalize_game(event.get("game"))
            if game in unique:
                covered.add(game)
    missing = [g.get("game") for key, g in unique.items() if key not in covered]
    schedule_dates = schedule.get("dates_eastern") or []
    valid_date = eastern_day in schedule_dates
    return {
        "date_eastern": eastern_day,
        "schedule_source": schedule.get("source"),
        "schedule_date_supported": valid_date,
        "scheduled_unfinished_games": len(unique),
        "games_with_confirmed_sportsbook_event_coverage": len(covered),
        "missing_game_names": missing,
        "coverage_complete": valid_date and len(missing) == 0,
        "line_provenance": "sportsbook event coverage; NOT PrizePicks line confirmation",
        "notes": ("No games on this date" if not unique and valid_date else
                  "No dated schedule available" if not valid_date else
                  "Missing event coverage is separate from whether a provider offers props"),
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--schedule", default="docs/nba_schedule.json")
    p.add_argument("--odds", default="docs/data.json")
    p.add_argument("--date", default="")
    p.add_argument("--fail-on-gap", action="store_true")
    args = p.parse_args()
    day = args.date or dt.datetime.now(EASTERN).date().isoformat()
    result = coverage(json.loads(Path(args.schedule).read_text()),
                      json.loads(Path(args.odds).read_text()), day)
    print(json.dumps(result, indent=2))
    if args.fail_on_gap and not result["coverage_complete"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()

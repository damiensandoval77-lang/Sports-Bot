"""Cheap schedule-derived guard for final-stat recovery; never grades live stats."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def due(schedule, now):
    games = schedule.get('games')
    if not isinstance(games, list) or len(games) != 272:
        # Bad schedule is an instruction to refresh, not silently skip recovery.
        return True
    for game in games:
        try:
            kickoff = datetime.fromisoformat(game['kickoff_utc'].replace('Z', '+00:00'))
            if kickoff.tzinfo is None:
                return True
            hours = (now - kickoff).total_seconds() / 3600
        except (KeyError, TypeError, ValueError):
            return True
        # Start before a normal final and retry well after long/overtime games.
        # Exporter still requires an independently verified FINAL schedule state.
        if 2 <= hours <= 12:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--schedule', default='docs/nfl/data/schedule_2026.json')
    parser.add_argument('--now')
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now.replace('Z', '+00:00')) if args.now else datetime.now(timezone.utc)
    try:
        schedule = json.loads(Path(args.schedule).read_text())
    except (OSError, ValueError):
        schedule = {}
    print('true' if due(schedule, now) else 'false')


if __name__ == '__main__':
    main()

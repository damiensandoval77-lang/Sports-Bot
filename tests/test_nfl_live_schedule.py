"""Regression: every published NFL fixture must have game-window cron coverage."""
import datetime as dt
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def values(field, low, high):
    result = set()
    for part in field.split(','):
        base, _, step = part.partition('/')
        if base == '*':
            begin, end = low, high
        elif '-' in base:
            begin, end = map(int, base.split('-'))
        else:
            begin = end = int(base)
        result.update(range(begin, end + 1, int(step or 1)))
    return result


def scheduled(moment, expressions):
    fields = [moment.minute, moment.hour, moment.day, moment.month,
              (moment.weekday() + 1) % 7]
    bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
    return any(all(value in values(field, *bound)
                   for value, field, bound in zip(fields, expr.split(), bounds))
               for expr in expressions)


class NFLRefreshScheduleTests(unittest.TestCase):
    def expressions(self):
        source = (ROOT / '.github/workflows/nfl-live-tracker.yml').read_text()
        return re.findall(r"cron:\s*'([^']+)'", source)

    def test_thursday_evening_is_friday_utc(self):
        self.assertTrue(scheduled(dt.datetime(2026, 11, 13, 1, 15), self.expressions()))
        self.assertTrue(scheduled(dt.datetime(2026, 11, 13, 5, 0), self.expressions()))

    def test_published_season_covered_from_pregame_through_four_hours(self):
        games = json.loads((ROOT / 'docs/nfl/data/schedule_2026.json').read_text())['games']
        self.assertEqual(len(games), 272)
        cron = self.expressions()
        missing = []
        for game in games:
            tip = dt.datetime.fromisoformat(game['kickoff_utc']).astimezone(dt.timezone.utc)
            start = tip - dt.timedelta(minutes=15)
            for offset in range(0, 256, 15):
                moment = start + dt.timedelta(minutes=offset)
                # Cron minute cadence is five minutes. Some future fixtures may
                # have off-cadence kickoff times; a poll within five minutes suffices.
                if not any(scheduled(moment + dt.timedelta(minutes=i), cron) for i in range(5)):
                    missing.append((game['game_id'], moment.isoformat()))
        self.assertEqual(missing, [])

    def test_offseason_not_scheduled(self):
        self.assertFalse(scheduled(dt.datetime(2027, 6, 6, 18, 0), self.expressions()))


if __name__ == '__main__':
    unittest.main()

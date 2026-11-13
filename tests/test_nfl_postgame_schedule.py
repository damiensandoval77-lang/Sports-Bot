import datetime as dt
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nfl_postgame_due import due
from test_nfl_live_schedule import scheduled


class PostgameScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedule = json.loads((ROOT / 'docs/nfl/data/schedule_2026.json').read_text())

    def expressions(self, name):
        return re.findall(r"cron:\s*'([^']+)'", (ROOT / '.github/workflows' / name).read_text())

    def test_all_272_games_have_repeated_postgame_export_and_grading(self):
        for game in self.schedule['games']:
            kickoff = dt.datetime.fromisoformat(game['kickoff_utc'])
            for hours in (3, 4, 5, 8):
                moment = kickoff + dt.timedelta(hours=hours)
                self.assertTrue(due(self.schedule, moment), game['game_id'])
                for name in ('nfl-boxscores-publish.yml', 'nfl-pick-grading.yml'):
                    self.assertTrue(any(scheduled(moment + dt.timedelta(minutes=i), self.expressions(name)) for i in range(61)), (game['game_id'], moment, name))

    def test_thursday_post_midnight_recovery(self):
        moment = dt.datetime(2026, 11, 13, 4, 35, tzinfo=dt.timezone.utc)
        self.assertTrue(due(self.schedule, moment))
        self.assertTrue(scheduled(moment, self.expressions('nfl-boxscores-publish.yml')))

    def test_no_unnecessary_offseason_export(self):
        self.assertFalse(due(self.schedule, dt.datetime(2027, 6, 1, tzinfo=dt.timezone.utc)))

    def test_invalid_schedule_requests_refresh(self):
        self.assertTrue(due({}, dt.datetime.now(dt.timezone.utc)))

    def test_delayed_source_background_retry_is_preserved(self):
        source = (ROOT / '.github/workflows/nfl-boxscores-publish.yml').read_text()
        self.assertIn("35 3,9,13,17,21 * 9-12,1-2 *", source)
        self.assertIn('github.event.schedule', source)

    def test_export_remains_final_only(self):
        source = (ROOT / 'scripts/export_nfl_boxscores.py').read_text()
        self.assertIn('g["status"]=="final"', source)
        self.assertIn('schedule-to-boxscore reconciliation', (ROOT / '.github/workflows/nfl-boxscores-publish.yml').read_text())


if __name__ == '__main__':
    unittest.main()

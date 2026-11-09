from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "docs/index.html").read_text()

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.inside = True
            self.scripts.append("")
    def handle_endtag(self, tag):
        if tag == "script":
            self.inside = False
    def handle_data(self, data):
        if self.inside:
            self.scripts[-1] += data

class DashboardScoreboardIntegrationTests(unittest.TestCase):
    def test_independent_scoreboard_checked_before_browser_fallback(self):
        start = HTML.index('async function refreshScoresOnly()')
        end = HTML.index('async function refresh()', start)
        fn = HTML[start:end]
        self.assertIn('fetchJSON("nba_scoreboard_independent.json")', fn)
        self.assertLess(fn.index('nba_scoreboard_independent.json'), fn.index('browserScoreboard(today)'))

    def test_only_fresh_healthy_snapshot_accepted(self):
        start = HTML.index('async function refreshScoresOnly()')
        end = HTML.index('async function refresh()', start)
        fn = HTML[start:end]
        self.assertIn('status==="OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES"', fn)
        self.assertIn('isRecent(independent.generated_at,2)', fn)
        self.assertIn('Array.isArray(independent.games)', fn)

    def test_existing_score_sources_still_available(self):
        start = HTML.index('async function refreshScoresOnly()')
        end = HTML.index('async function refresh()', start)
        fn = HTML[start:end]
        self.assertIn('fetchJSON("nba_schedule.json")', fn)
        self.assertIn('browserScoreboard(today)', fn)
        self.assertIn('mergeScoreSchedules', fn)

    def test_has_inline_javascript_to_syntax_check(self):
        parsed = Scripts()
        parsed.feed(HTML)
        self.assertTrue(any('refreshScoresOnly' in s for s in parsed.scripts))

if __name__ == "__main__":
    unittest.main()

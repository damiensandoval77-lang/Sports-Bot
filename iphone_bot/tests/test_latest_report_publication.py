"""Prevent report-publish retry loops from reintroducing obsolete snapshots."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
class LatestReportPublicationTests(unittest.TestCase):
    def _body(self,path):
        return (ROOT/path).read_text()

    def test_unified_readiness_rechecks_after_fetch_on_each_push_attempt(self):
        s=self._body(".github/workflows/unified-dames-picks-readiness.yml")
        self.assertIn("python -m iphone_bot.unified_dames_readiness || rc=$?",s)
        segment=s[s.index("for n in 1 2 3 4 5 6; do"):]
        self.assertLess(segment.index("git reset --hard origin/main"),
                        segment.index("python -m iphone_bot.unified_dames_readiness || rc=$?"))
        self.assertLess(segment.index("python -m iphone_bot.unified_dames_readiness || rc=$?"),
                        segment.index("git add docs/dames-picks/unified_readiness.json"))
        self.assertNotIn('cp "$RUNNER_TEMP/unified_readiness.json"',s)

    def test_capture_rechecks_quotes_and_frozen_models_after_each_fetch(self):
        s=self._body(".github/workflows/nba-tonight-capture-gradeability.yml")
        part=s[s.index("for attempt in 1 2 3 4 5; do"):]
        assert part.index("git reset --hard origin/main") < part.index(
            "python -m iphone_bot.audit_primary_model_missing") < part.index(
            "python -m iphone_bot.tonight_capture_gradeability || rc=$?") < part.index(
            "git add docs/tonight_capture_gradeability.json")
        self.assertNotIn('cp "$RUNNER_TEMP/tonight_capture_gradeability.json"',s)

    def test_release_gate_uses_new_reports_instead_of_stale_copies(self):
        s=self._body(".github/workflows/dames-picks-app-release-gate.yml")
        self.assertLess(s.index("git reset --hard origin/main"),
                        s.index("python -m iphone_bot.app_release_gate || rc=$?"))

if __name__=="__main__":
    unittest.main()

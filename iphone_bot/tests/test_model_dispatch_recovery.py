"""Contracts for credit-free retry of missing frozen predictions."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import workflow_contract as W
ROOT=Path(__file__).resolve().parents[2]

class RecoveryHandoffTests(unittest.TestCase):
    def test_unchanged_board_can_still_recover_model_without_paid_fetch(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        part=text.split("      - name: Recover missing frozen models even when provider lines are unchanged",1)[1]
        cond=W.condition("nba-prizepicks-site-publish.yml","Recover missing frozen models even when provider lines are unchanged")
        self.assertTrue(W.runs_after_success(cond),cond)
        self.assertFalse(W.change_gated(cond),cond)
        self.assertIn("gh workflow run nba-new-ai-all-markets.yml --ref main",part)
        self.assertIn("createdAt,headBranch",part)
        self.assertIn('.headBranch == "main"',part)
        self.assertIn("60*60",part)
        self.assertIn("now+dt.timedelta(hours=24)",part)
        self.assertNotIn("fetch_prizepicks.py",part)
    def test_pull_requests_only_run_offline_source_contracts(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        self.assertIn("pull_request:",text)
        for n in ("Build small read-only PrizePicks board and coverage",
                  "Publish no-cost website research status",
                  "Recover missing frozen models even when provider lines are unchanged"):
            self.assertTrue(W.excluded_from_pull_requests(W.condition("nba-prizepicks-site-publish.yml",n)),n)
    def test_source_archive_and_existing_direct_handoffs_remain(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        self.assertIn("python -m iphone_bot.archive_prizepicks_pregame_lines",text)
        self.assertIn("gh workflow run nba-tonight-capture-gradeability.yml --ref main",text)
        self.assertIn("gh workflow run publish_live_pp_ai_join.yml --ref main",text)
if __name__=="__main__":unittest.main()

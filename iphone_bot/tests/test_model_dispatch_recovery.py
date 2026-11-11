"""Contract for unattended pretip model recovery after no-change provider snapshots."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class RecoveryHandoffTests(unittest.TestCase):
    def test_unchanged_board_can_still_recover_model_without_paid_fetch(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        part=text.split("      - name: Recover missing frozen models even when provider lines are unchanged",1)[1]
        self.assertIn("if: success()",part)
        self.assertNotIn("steps.publish.outputs.changed == 'true'",part.split("      - name:",1)[0])
        self.assertIn("gh workflow run nba-new-ai-all-markets.yml --ref main",part)
        self.assertIn("createdAt,headBranch",part)
        self.assertIn('.headBranch == "main"',part)
        self.assertIn("60*60",part)
        self.assertIn("now+dt.timedelta(hours=24)",part)
        self.assertNotIn("fetch_prizepicks.py",part)
    def test_source_archive_and_existing_direct_handoffs_remain(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        self.assertIn("python -m iphone_bot.archive_prizepicks_pregame_lines",text)
        self.assertIn("gh workflow run nba-tonight-capture-gradeability.yml --ref main",text)
        self.assertIn("gh workflow run publish_live_pp_ai_join.yml --ref main",text)
if __name__=="__main__":unittest.main()

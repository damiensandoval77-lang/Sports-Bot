"""Static regression of no-cost site-to-AI recovery dispatch."""
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/nba-prizepicks-site-publish.yml"
QUICK_JOIN = Path(__file__).resolve().parents[2] / ".github/workflows/publish_live_pp_ai_join.yml"

class UnchangedSnapshotRecoveryTests(unittest.TestCase):
    def test_no_cost_join_dispatch_after_successful_site_publish_without_diff(self):
        text = WORKFLOW.read_text()
        block = text.split("- name: Recover AI-versus-line research even when saved provider snapshot is unchanged",1)[1]
        block = block.split("\n      - name:",1)[0]
        self.assertIn("if: success()", block)
        self.assertIn("gh workflow run publish_live_pp_ai_join.yml --ref main", block)
        self.assertNotIn("steps.publish.outputs.changed", block)
    def test_paid_provider_refresh_not_run_in_downstream_join(self):
        text = QUICK_JOIN.read_text()
        self.assertIn("python -u -m iphone_bot.publish_live_pp_ai_join", text)
        self.assertNotIn("PRIZEPICKS_API_KEY", text)
        self.assertNotIn("fetch_prizepicks", text)
    def test_trained_ai_stays_change_gated(self):
        text = WORKFLOW.read_text()
        block = text.split("- name: Generate actual player AI projections immediately from new authentic lines",1)[1]
        block = block.split("\n      - name:",1)[0]
        self.assertIn("if: steps.publish.outputs.changed == 'true'", block)

if __name__ == "__main__":
    unittest.main()

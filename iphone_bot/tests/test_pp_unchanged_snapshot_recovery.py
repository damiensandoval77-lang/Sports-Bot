"""Recovery dispatch contracts independent of conditional spelling."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import workflow_contract as W
ROOT=Path(__file__).resolve().parents[2]
QUICK_JOIN=ROOT/".github/workflows/publish_live_pp_ai_join.yml"
WF="nba-prizepicks-site-publish.yml"

class UnchangedSnapshotRecoveryTests(unittest.TestCase):
    def test_no_cost_join_dispatch_after_successful_site_publish_without_diff(self):
        name="Recover AI-versus-line research even when saved provider snapshot is unchanged"
        cond=W.condition(WF,name)
        self.assertTrue(W.runs_after_success(cond),cond)
        self.assertIn("gh workflow run publish_live_pp_ai_join.yml --ref main",W.step(WF,name)["run"])
        self.assertFalse(W.change_gated(cond),cond)
    def test_paid_provider_refresh_not_run_in_downstream_join(self):
        text=QUICK_JOIN.read_text()
        self.assertIn("python -u -m iphone_bot.publish_live_pp_ai_join",text)
        self.assertNotIn("PRIZEPICKS_API_KEY",text)
        self.assertNotIn("fetch_prizepicks",text)
    def test_trained_ai_stays_change_gated(self):
        cond=W.condition(WF,"Generate actual player AI projections immediately from new authentic lines")
        self.assertTrue(W.change_gated(cond),cond)
if __name__=="__main__":unittest.main()

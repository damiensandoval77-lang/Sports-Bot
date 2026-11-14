from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import workflow_contract as W
import unittest
ROOT=Path(__file__).resolve().parents[2]
SITE=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
TRAINED=(ROOT/".github/workflows/nba-prizepicks-ai-board.yml").read_text()
LIGHT=(ROOT/".github/workflows/publish_live_pp_ai_join.yml").read_text()
COLLECT=(ROOT/".github/workflows/nba-prizepicks-full-slate.yml").read_text()

class PublicationHandoffTests(unittest.TestCase):
    def test_site_refresh_matches_afternoon_provider_window(self):
        self.assertIn("- cron: '16,46 0,16-23 * * *'",SITE)
        self.assertIn("- cron: '08 1,17,19,21,23,0 * * *'",TRAINED)
    def test_provider_refresh_windows_limit_avoidable_stale_gaps_and_credit_calls(self):
        # Native requests are free; half-hour captures stay within 60m TTL.
        self.assertIn("- cron: '28,58 0,16-23 * * *'",COLLECT)
        minutes=[h*60+m for h in range(16,25) for m in (28,58)]
        self.assertLessEqual(max(b-a for a,b in zip(minutes,minutes[1:])),30)
        self.assertIn("gh workflow run nba-prizepicks-site-publish.yml --ref main",COLLECT)
        self.assertNotIn("PRIZEPICKS_API_KEY",COLLECT)
        self.assertIn("python -m iphone_bot.fetch_native_prizepicks",COLLECT)

    def test_both_model_paths_trigger_when_real_lines_published(self):
        self.assertIn("gh workflow run nba-prizepicks-ai-board.yml --ref main",SITE)
        self.assertIn("gh workflow run nba-new-ai-all-markets.yml --ref main",SITE)
        self.assertIn("gh workflow run publish_live_pp_ai_join.yml --ref main",SITE)
        self.assertTrue(W.change_gated(W.condition("nba-prizepicks-site-publish.yml","Generate actual player AI projections immediately from new authentic lines")))
    def test_no_paid_provider_calls_in_join_workflow(self):
        self.assertNotIn("PRIZEPICKS_API_KEY",LIGHT)
        self.assertNotIn("fetch_prizepicks.py",LIGHT)
        self.assertIn("python -u -m iphone_bot.publish_live_pp_ai_join",LIGHT)
        self.assertIn("docs/ai_prizepicks_quick_join.json",LIGHT)

if __name__=="__main__":
    unittest.main()

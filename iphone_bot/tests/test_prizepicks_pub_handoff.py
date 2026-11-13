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
        self.assertIn("- cron: '46 0,16,18,20,22,23 * * *'",SITE)
        self.assertIn("- cron: '08 1,17,19,21,23,0 * * *'",TRAINED)
    def test_provider_refresh_windows_limit_avoidable_stale_gaps_and_credit_calls(self):
        # Previously only 16:28, 21:28, 23:28 UTC: five hours of unavoidably
        # stale 90-minute lines. Now at most two hours between pretip captures.
        self.assertIn("- cron: '28 0,16,18,20,22,23 * * *'",COLLECT)
        hours=[16,18,20,22,23,24]  # 00:28 UTC belongs to next day's late games
        self.assertLessEqual(max(b-a for a,b in zip(hours,hours[1:])),2)
        self.assertEqual(len(hours),6)
        self.assertIn("MAX_PAGES=4", (ROOT/"iphone_bot/fetch_prizepicks.py").read_text())
        self.assertIn("if err.code!=429:raise", (ROOT/"iphone_bot/fetch_prizepicks.py").read_text())
        self.assertIn("gh workflow run nba-prizepicks-site-publish.yml --ref main",COLLECT)
        self.assertIn("PRIZEPICKS_API_KEY: ${{ secrets.PRIZEPICKS_API_KEY }}",COLLECT)

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

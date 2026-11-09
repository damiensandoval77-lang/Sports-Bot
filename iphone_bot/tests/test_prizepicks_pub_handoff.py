from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
SITE=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
TRAINED=(ROOT/".github/workflows/nba-prizepicks-ai-board.yml").read_text()
LIGHT=(ROOT/".github/workflows/publish_live_pp_ai_join.yml").read_text()

class PublicationHandoffTests(unittest.TestCase):
    def test_site_refresh_matches_afternoon_provider_window(self):
        self.assertIn("- cron: '46 0,16,18,20,22,23 * * *'",SITE)
        self.assertIn("- cron: '08 1,17,19,21,23,0 * * *'",TRAINED)
    def test_both_model_paths_trigger_when_real_lines_published(self):
        self.assertIn("gh workflow run nba-prizepicks-ai-board.yml --ref main",SITE)
        self.assertIn("gh workflow run publish_live_pp_ai_join.yml --ref main",SITE)
        self.assertIn("if: steps.publish.outputs.changed == 'true'",SITE)
    def test_no_paid_provider_calls_in_join_workflow(self):
        self.assertNotIn("PRIZEPICKS_API_KEY",LIGHT)
        self.assertNotIn("fetch_prizepicks.py",LIGHT)
        self.assertIn("python -u -m iphone_bot.publish_live_pp_ai_join",LIGHT)
        self.assertIn("docs/ai_prizepicks_quick_join.json",LIGHT)

if __name__=="__main__":
    unittest.main()

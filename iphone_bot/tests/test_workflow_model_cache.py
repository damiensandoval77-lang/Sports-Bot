"""Regression contract: new provider quotes must never require historical ML retraining."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

class FastPretipPipelineTests(unittest.TestCase):
    def test_historical_models_are_reused_when_training_code_is_unchanged(self):
        text=(ROOT/".github/workflows/nba-new-ai-all-markets.yml").read_text()
        self.assertIn("actions/cache/restore@v4",text)
        self.assertIn("actions/cache/save@v4",text)
        self.assertIn("steps.historical_cache.outputs.cache-hit != 'true'",text)
        self.assertIn("models/nba/research/lagged_matchup_all_markets.joblib",text)
        self.assertIn("models/nba/research/lagged_matchup_2022_24.joblib",text)
        self.assertIn("docs/lagged_matchup_all_market_validation.json",text)
        self.assertLess(text.index("Verify four-market backtest completeness"),
                        text.index("actions/cache/save@v4"))
        self.assertLess(text.index("actions/cache/save@v4"),
                        text.index("Fetch current season and verify actual standard PrizePicks lines"))

    def test_real_line_ingestion_dispatches_current_model_producer(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        self.assertIn("gh workflow run nba-new-ai-all-markets.yml --ref main",text)
        self.assertIn("steps.publish.outputs.changed == 'true'",text)
        self.assertIn("docs/prizepicks_pregame_line_archive.json",text)

    def test_post_model_publish_triggers_independent_capture_audit(self):
        text=(ROOT/".github/workflows/nba-new-ai-all-markets.yml").read_text()
        self.assertIn("gh workflow run nba-tonight-capture-gradeability.yml --ref main",text)
        self.assertIn("python -m iphone_bot.merge_new_ai_publishing",text)
        self.assertIn("python -m iphone_bot.injury_refresh_integrity",text)

if __name__=="__main__":
    unittest.main()

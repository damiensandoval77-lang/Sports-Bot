"""Verify the deployed readiness job repairs free live stats before deciding health."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
class ProductionLiveRecoveryContract(unittest.TestCase):
    def test_live_player_refresh_runs_before_readiness(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        self.assertIn("python -m iphone_bot.refresh_nba_player_boxscores",text)
        self.assertLess(text.index("name: Recover authentic live NBA player totals"),
                        text.index("name: Evaluate actual published NBA input freshness"))
        self.assertIn("publishable_observations(d)",text)
    def test_safe_merge_and_publish_uses_latest_branch(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        a=text.index("git reset --hard origin/main")
        b=text.index("python -m iphone_bot.merge_nba_player_boxscore_publish")
        c=text.index("git add docs/production_readiness.json")
        self.assertLess(a,b)
        self.assertLess(b,c)
        self.assertIn("--incoming \"$RUNNER_TEMP/nba_player_tracking_independent.json\"",text)
        self.assertNotIn("merge_nba_player_boxscore_publish \\\\",text)
    def test_source_is_free_and_existing_safeguards_still_run(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        self.assertIn("python -m iphone_bot.merge_scoreboard_snapshot",text)
        self.assertIn("python -m iphone_bot.readiness_recovery",text)
        self.assertNotIn("PRIZEPICKS_API_KEY",text)
if __name__=="__main__":unittest.main()

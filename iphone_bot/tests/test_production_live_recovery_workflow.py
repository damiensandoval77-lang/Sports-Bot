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
    def test_report_is_recomputed_after_latest_inputs_merge_on_each_push_attempt(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        start=text.index("for attempt in 1 2 3 4 5")
        reset=text.index("git reset --hard origin/main",start)
        merge=text.index("python -m iphone_bot.merge_nba_player_boxscore_publish",reset)
        evaluate=text.index('python -u -m iphone_bot.production_readiness || test "$?" -eq 2',merge)
        stage=text.index("git add docs/production_readiness.json",evaluate)
        self.assertLess(reset,merge)
        self.assertLess(merge,evaluate)
        self.assertLess(evaluate,stage)
        self.assertNotIn('cp "$RUNNER_TEMP/production_readiness.json"',text)
        final=text.split("name: Fail visibly when bot is not ready for reliable picks",1)[1]
        self.assertIn('.status == "READY"',final)
        self.assertNotIn("steps.check.outcome == 'failure'",final)

    def test_recompute_accepts_health_failure_but_not_execution_failure(self):
        import subprocess
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        command=next(line.strip() for line in text.splitlines()
                     if 'production_readiness || test' in line)
        for result,expected in [(0,0),(2,0),(1,1),(127,1)]:
            with self.subTest(result=result):
                script='python() { return '+str(result)+'; }; '+command
                proc=subprocess.run(['bash','-e','-c',script],capture_output=True)
                self.assertEqual(proc.returncode,expected)

    def test_source_is_free_and_existing_safeguards_still_run(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        self.assertIn("python -m iphone_bot.merge_scoreboard_snapshot",text)
        self.assertIn("python -m iphone_bot.readiness_recovery",text)
        self.assertNotIn("PRIZEPICKS_API_KEY",text)

    def test_failed_comparison_publisher_reaches_bounded_recovery(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        condition=next(line.strip() for line in text.splitlines() if line.strip().startswith("if: github.event_name"))
        self.assertIn("(github.event.workflow_run.name == 'Publish lightweight verified PrizePicks AI comparisons' && github.event.workflow_run.conclusion == 'failure')", condition)
        self.assertIn("nba-prizepicks-full-slate.yml) cooldown_minutes=90", text)
        self.assertIn('(.status != "completed")', text)
        self.assertIn('($paid == "true" or .conclusion == "success")', text)
        self.assertIn('python -m iphone_bot.readiness_recovery', text)

if __name__=="__main__":unittest.main()

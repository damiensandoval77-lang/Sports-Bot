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
        self.assertNotIn("conclusion", condition)
        self.assertIn("head_branch == 'main'", condition)
        self.assertIn("head_repository.full_name == github.repository", condition)
        self.assertIn("event != 'pull_request'", condition)
        self.assertIn("nba-prizepicks-full-slate.yml) cooldown_minutes=90", text)
        self.assertIn('.status != "completed"', text)
        self.assertIn('($paid == "true" or .conclusion == "success")', text)
        self.assertIn('python -m iphone_bot.readiness_recovery', text)

    def test_free_live_recovery_does_not_wait_until_public_ttl(self):
        import re
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        for workflow in ("independent_scoreboard_refresh.yml", "independent_nba_player_boxscores.yml", "verify_unified_dames_browser.yml"):
            with self.subTest(workflow=workflow):
                cooldown=int(re.search(re.escape(workflow)+r"\) cooldown_minutes=(\d+)", text).group(1))
                self.assertEqual(cooldown,5)
        # Free retries do not remove paid-call caps or active-run deduplication.
        self.assertIn("nba-prizepicks-full-slate.yml) cooldown_minutes=90",text)
        self.assertIn("nba-new-ai-all-markets.yml) cooldown_minutes=90",text)
        self.assertIn('.status != "completed"',text)
        self.assertIn("failure_backoff_minutes=5",text)

    def test_failure_completion_cannot_immediately_redispatch_itself(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        self.assertIn("failure_backoff_minutes=5",text)
        self.assertIn("failure_backoff_minutes=15",text)
        self.assertIn(".updatedAt | fromdateiso8601",text)
        self.assertIn("$failed_cutoff",text)
        self.assertIn('$paid != "true" and .conclusion != "success"',text)

    def test_actual_cooldown_filter_bounds_failures_without_blocking_other_branches(self):
        import json, subprocess
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        expression=text.split('echo false)" \'',1)[1].split("')",1)[0]
        def recent(paid,branch,status,conclusion,created,updated):
            row={"headBranch":branch,"status":status,"conclusion":conclusion,
                 "createdAt":created,"updatedAt":updated}
            p=subprocess.run(["jq","--argjson","cutoff","3600","--argjson","failed_cutoff","6900",
                "--arg","paid",paid,expression],input=json.dumps([row]),text=True,capture_output=True,check=True)
            return int(p.stdout)
        early="1970-01-01T00:00:00Z"; recent_time="1970-01-01T01:59:00Z"
        for conclusion in ("failure","cancelled","timed_out"):
            self.assertEqual(recent("false","main","completed",conclusion,early,recent_time),1)
            self.assertEqual(recent("false","main","completed",conclusion,early,early),0)
            self.assertEqual(recent("false","feature","completed",conclusion,early,recent_time),0)
        self.assertEqual(recent("true","main","completed","failure",recent_time,recent_time),1)
        self.assertEqual(recent("false","main","completed","success",recent_time,recent_time),1)
        self.assertEqual(recent("false","main","in_progress",None,early,early),1)

    def test_every_recovery_producer_completion_is_subscribed(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        subscribed=text.split("workflows:",1)[1].split("types:",1)[0]
        for filename in ("nba-schedule.yml", "nba-no-line-daily-projections.yml",
                         "nba-prizepicks-full-slate.yml", "nba-new-ai-all-markets.yml",
                         "nba-prizepicks-site-publish.yml", "independent_scoreboard_refresh.yml",
                         "independent_nba_player_boxscores.yml", "nba-live-tracker-backup.yml",
                         "verify_unified_dames_browser.yml"):
            with self.subTest(workflow=filename):
                name=(ROOT/".github/workflows"/filename).read_text().splitlines()[0].removeprefix("name: ").strip()
                self.assertIn("- "+name, subscribed)

    def test_failed_source_events_reach_audit_but_untrusted_events_do_not(self):
        text=(ROOT/".github/workflows/production_readiness.yml").read_text()
        condition=next(line.strip()[4:] for line in text.splitlines() if line.strip().startswith("if: github.event_name"))
        # Execute the exact workflow boolean expression against representative
        # event values, not a separate copy of the routing logic.
        for outcome in ("success", "failure", "timed_out", "cancelled"):
            for branch,repo,event,expected in (("main","owner/repo","schedule",True),
                    ("other","owner/repo","push",False),
                    ("main","attacker/fork","push",False),
                    ("main","owner/repo","pull_request",False)):
                values={"github.event_name":"workflow_run", "github.event.workflow_run.head_branch":branch,
                        "github.event.workflow_run.head_repository.full_name":repo,
                        "github.event.workflow_run.event":event,
                        "github.event.workflow_run.conclusion":outcome,"github.repository":"owner/repo"}
                expression=condition
                for key in sorted(values,key=len,reverse=True):
                    expression=expression.replace(key,repr(values[key]))
                self.assertEqual(eval(expression.replace("||"," or ").replace("&&"," and "),{"__builtins__":{}}),expected)

if __name__=="__main__":unittest.main()

from pathlib import Path
import unittest

WORKFLOW = (Path(__file__).resolve().parents[2] / ".github/workflows/independent_scoreboard_refresh.yml").read_text()

class ScoreboardFailureWorkflowTests(unittest.TestCase):
    def test_live_cadence_leaves_recovery_headroom_before_score_expiry(self):
        import re
        crons = re.findall(r'cron: "([^"]+)"', WORKFLOW)
        live = [c.split() for c in crons if c.split()[1] == "0-8,23"]
        self.assertEqual(len(live), 1)
        minutes = sorted(map(int, live[0][0].split(",")))
        gaps = [b-a for a,b in zip(minutes, minutes[1:]+[minutes[0]+60])]
        self.assertLessEqual(max(gaps), 5)
        self.assertIn("8,28,48 9-22 * * *", crons)

    def test_refresh_failure_is_not_silenced(self):
        self.assertIn("id: refresh",WORKFLOW)
        self.assertIn("continue-on-error: true",WORKFLOW)
        self.assertIn("steps.refresh.outcome == 'failure'",WORKFLOW)
        self.assertIn("exit 1",WORKFLOW)

    def test_failure_is_committed_before_job_fails(self):
        self.assertLess(WORKFLOW.index("Commit latest scoreboard observation"),
                        WORKFLOW.index("Fail workflow if provider refresh failed"))
        self.assertIn("git add docs/nba_scoreboard_independent.json",WORKFLOW)
        self.assertIn("if: always() && github.event_name != 'pull_request'",WORKFLOW)

    def test_official_schedule_changes_trigger_scoreboard_revalidation(self):
        push_section=WORKFLOW.split("  push:",1)[1].split("  schedule:",1)[0]
        self.assertIn('"docs/nba_schedule.json"',push_section)
        self.assertIn('"docs/verified_official_nba_fixtures.json"',push_section)

    def test_pull_requests_do_not_write_runtime_data(self):
        self.assertIn("steps.refresh.outcome != 'skipped'",WORKFLOW)
        self.assertIn("github.event_name != 'pull_request'",WORKFLOW)

if __name__ == "__main__":
    unittest.main()

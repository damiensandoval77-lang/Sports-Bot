"""Contracts for credit-free retry of missing frozen predictions."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import workflow_contract as W
ROOT=Path(__file__).resolve().parents[2]

class RecoveryHandoffTests(unittest.TestCase):
    def test_unchanged_board_can_still_recover_model_without_paid_fetch(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        part=text.split("      - name: Recover missing frozen models even when provider lines are unchanged",1)[1]
        cond=W.condition("nba-prizepicks-site-publish.yml","Recover missing frozen models even when provider lines are unchanged")
        self.assertTrue(W.runs_after_success(cond),cond)
        self.assertFalse(W.change_gated(cond),cond)
        self.assertIn("gh workflow run nba-new-ai-all-markets.yml --ref main",part)
        self.assertIn("createdAt,headBranch",part)
        self.assertIn("python -m iphone_bot.model_dispatch_recovery --source docs/prizepicks_model_input.json",part)
        self.assertIn("now+dt.timedelta(hours=24)",part)
        self.assertNotIn("fetch_prizepicks.py",part)
    def test_pull_requests_only_run_offline_source_contracts(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        self.assertIn("pull_request:",text)
        for n in ("Build small read-only PrizePicks board and coverage",
                  "Publish no-cost website research status",
                  "Recover missing frozen models even when provider lines are unchanged"):
            self.assertTrue(W.excluded_from_pull_requests(W.condition("nba-prizepicks-site-publish.yml",n)),n)
    def test_source_archive_and_existing_direct_handoffs_remain(self):
        text=(ROOT/".github/workflows/nba-prizepicks-site-publish.yml").read_text()
        self.assertIn("python -m iphone_bot.archive_prizepicks_pregame_lines",text)
        self.assertIn("gh workflow run nba-tonight-capture-gradeability.yml --ref main",text)
        self.assertIn("gh workflow run publish_live_pp_ai_join.yml --ref main",text)


class SourceAwareDispatchTests(unittest.TestCase):
    def setUp(self):
        import datetime as dt
        self.now = dt.datetime(2026,11,12,23,0,tzinfo=dt.timezone.utc)
        self.source = '2026-11-12T22:55:00Z'
    def run_record(self, status='in_progress', created='2026-11-12T22:54:00Z', conclusion=None):
        return dict(status=status,createdAt=created,conclusion=conclusion,headBranch='main')
    def covered(self, rows):
        from iphone_bot.model_dispatch_recovery import covering_runs
        return covering_runs(rows,self.source,self.now)
    def test_new_source_during_older_active_run_queues_successor(self):
        self.assertFalse(self.covered([self.run_record()]))
    def test_newer_pending_successor_coalesces_repeated_source_events(self):
        for status in ('queued','pending','waiting','requested','in_progress'):
            self.assertEqual(len(self.covered([self.run_record(),self.run_record(status,'2026-11-12T22:56:00Z')])),1)
    def test_equal_source_time_is_covered(self):
        self.assertEqual(len(self.covered([self.run_record(created=self.source)])),1)
    def test_old_success_does_not_hide_new_source(self):
        self.assertFalse(self.covered([self.run_record('completed',conclusion='success')]))
    def test_recent_success_covering_source_suppresses_duplicate(self):
        self.assertEqual(len(self.covered([self.run_record('completed','2026-11-12T22:56:00Z','success')])),1)
    def test_failed_cancelled_or_skipped_runs_allow_recovery(self):
        for result in ('failure','cancelled','skipped','timed_out',None):
            self.assertFalse(self.covered([self.run_record('completed','2026-11-12T22:56:00Z',result)]))
    def test_old_success_cooldown_expires_but_active_does_not(self):
        self.source='2026-11-12T21:00:00Z'
        self.assertFalse(self.covered([self.run_record('completed','2026-11-12T21:30:00Z','success')]))
        self.assertTrue(self.covered([self.run_record('in_progress','2026-11-12T21:30:00Z')]))
    def test_other_branches_and_invalid_runs_do_not_cover_main(self):
        row=self.run_record(created='2026-11-12T22:56:00Z');row['headBranch']='feature'
        self.assertFalse(self.covered([row,self.run_record(created='bad')]))
    def test_invalid_or_future_source_fails_visibly_instead_of_false_coverage(self):
        for source in (None,'bad','2026-11-12T22:55:00','2026-11-13T00:00:00Z'):
            self.source=source
            with self.assertRaises(ValueError):self.covered([])

if __name__=='__main__':unittest.main()

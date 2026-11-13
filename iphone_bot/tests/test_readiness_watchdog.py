import datetime as dt
import json
import unittest
from iphone_bot.readiness_watchdog import evaluate

NOW = dt.datetime(2026,11,13,14,0,tzinfo=dt.timezone.utc)

class WatchdogTests(unittest.TestCase):
    def run_case(self, runs):
        calls=[]
        def command(args):
            calls.append(args)
            return json.dumps(runs) if args[0]=='run' else ''
        return evaluate(now=NOW,command=command),calls

    def row(self, **kw):
        return dict(dict(headBranch='main',event='workflow_run',status='completed',updatedAt='2026-11-13T13:00:00Z'),**kw)

    def test_idle_dispatches_only_controller(self):
        r,c=self.run_case([self.row()]);self.assertEqual(r['status'],'DISPATCHED')
        self.assertEqual(c[-1],['workflow','run','production_readiness.yml','--ref','main'])

    def test_recent_failed_execution_also_suppresses_retry(self):
        r,c=self.run_case([self.row(updatedAt='2026-11-13T13:50:00Z',conclusion='failure')])
        self.assertEqual(r['reason'],'CONTROLLER_RECENT');self.assertEqual(len(c),1)

    def test_active_suppresses(self):
        for status in ['queued','pending','waiting','requested','in_progress']:
            r,c=self.run_case([self.row(status=status)])
            self.assertEqual(r['reason'],'CONTROLLER_ACTIVE');self.assertEqual(len(c),1)

    def test_foreign_branch_and_pr_do_not_suppress(self):
        r,c=self.run_case([self.row(headBranch='feature',status='in_progress'),self.row(event='pull_request',status='in_progress')])
        self.assertEqual(r['status'],'DISPATCHED')

    def test_invalid_inventory_fails_closed(self):
        for runs in [{},[self.row(status='unknown')],[self.row(updatedAt='bad')],[self.row(updatedAt='2026-11-14T00:00:00Z')]]:
            r,c=self.run_case(runs);self.assertEqual(r['status'],'BLOCKED');self.assertEqual(len(c),1)

    def test_command_failure_is_redacted(self):
        def command(args): raise RuntimeError('secret response')
        r=evaluate(now=NOW,command=command)
        self.assertEqual(r['status'],'BLOCKED');self.assertNotIn('secret',json.dumps(r))

    def test_dispatch_failure(self):
        def command(args):
            if args[0]=='run': return '[]'
            raise RuntimeError('secret')
        self.assertEqual(evaluate(now=NOW,command=command)['reason'],'DISPATCH_FAILED')

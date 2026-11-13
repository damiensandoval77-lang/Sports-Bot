import unittest
from types import SimpleNamespace
from iphone_bot.push_research_snapshot import push,can_replay
class SnapshotPush(unittest.TestCase):
    def test_input_changes_require_recompute(self):
        for p in ['docs/prizepicks.json','docs/injury_context.json','docs/lagged_matchup_all_market_ledger.json','iphone_bot/short_history_inference.py','data/new.csv','requirements.txt']:
            self.assertFalse(can_replay([p]))
        self.assertTrue(can_replay(['docs/nfl/data/live_2026.json','docs/production_readiness.json']))
    def test_unrelated_update_rebases_and_retries(self):
        calls=[];responses=[(0,'docs/short_history_model.json'),(1,''),(0,''),(0,'docs/nfl/data/live_2026.json'),(0,''),(0,'')]
        def run(args,**kw):
            calls.append(args);code,out=responses.pop(0);return SimpleNamespace(returncode=code,stdout=out)
        self.assertEqual(push(run),0)
        self.assertIn(['git','rebase','--autostash','origin/main'],calls)
        self.assertEqual(sum(x[1]=='push' for x in calls),2)
    def test_changed_inputs_no_rebase(self):
        calls=[];responses=[(0,'docs/short_history_model.json'),(1,''),(0,''),(0,'docs/injury_context.json')]
        def run(args,**kw):
            calls.append(args);code,out=responses.pop(0);return SimpleNamespace(returncode=code,stdout=out)
        self.assertEqual(push(run),1);self.assertFalse(any(x[1]=='rebase' for x in calls))
    def test_conflicting_output_aborts(self):
        calls=[];responses=[(0,'docs/short_history_model.json'),(1,''),(0,''),(0,'docs/short_history_model.json'),(1,''),(0,'')]
        def run(args,**kw):
            calls.append(args);code,out=responses.pop(0);return SimpleNamespace(returncode=code,stdout=out)
        self.assertEqual(push(run),1);self.assertEqual(calls[-1],['git','rebase','--abort'])
    def test_other_committed_files_rejected(self):
        self.assertEqual(push(lambda *a,**kw:SimpleNamespace(returncode=0,stdout='docs/primary.json')),1)

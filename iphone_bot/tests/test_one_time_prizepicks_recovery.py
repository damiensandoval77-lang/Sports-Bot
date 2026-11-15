import copy
import datetime as dt
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from iphone_bot import one_time_prizepicks_recovery as recovery

NOW = recovery.START+dt.timedelta(minutes=1)
PRIOR = {'authorization_id':recovery.AUTHORIZATION,'status':'UNUSED','last_paid_read_at':'2026-11-14T21:18:46Z'}

def fixture():
    row={'id':'test','is_demo':False,'league':'NBA','status':'active',
        'player':{'name':'Test Player','team':'BOS'},
        'event':{'opponent':'MIA','starts_at':'2026-11-15T23:00:00Z'},
        'market':{'stat':'Points','period':'Full game'},'line':20.5,
        'observed_at':NOW.isoformat(),'sides':['more','less'],'tier':'standard'}
    page={'meta':{'mode':'live','source_status':'fresh','next_cursor':'do_not_fetch'},'data':[row]}
    schedule={'games':[{'game':'Boston Celtics @ Miami Heat','start':'2026-11-15T23:00:00Z'}]}
    return page,schedule

class RecoveryTests(unittest.TestCase):
    def test_previous_authorization_cannot_be_reused(self):
        root=Path(__file__).resolve().parents[2]
        prior=json.loads((root/'docs/prizepicks_one_time_recovery_20261114.json').read_text())
        self.assertEqual(prior['status'], 'FRESH_PARTIAL_BOARD_PUBLISHED')
        self.assertEqual(prior['charged_credits'], '10')
        with self.assertRaises(ValueError): recovery.claim(prior,NOW,'run')

    def test_window_and_one_shot_cooldown(self):
        for when in (recovery.START-dt.timedelta(seconds=1), recovery.END):
            with self.assertRaises(ValueError): recovery.claim(PRIOR,when,'run')
        claimed=recovery.claim(PRIOR,NOW,'run')
        with self.assertRaises(ValueError):recovery.claim(claimed,NOW,'second')
        with self.assertRaises(ValueError):recovery.claim(PRIOR,NOW,'run','2')
        with self.assertRaises(ValueError):recovery.claim({},NOW,'run')

    def test_single_request_fresh_partial_board_preserves_observed_time(self):
        page,schedule=fixture(); reader=Mock(return_value=(page,{'charged_credits':'10','remaining_credits_header':'0'}))
        receipt,board=recovery.execute(recovery.claim(PRIOR,NOW,'run'),schedule,NOW,'run','secret',reader,clock=lambda:NOW)
        reader.assert_called_once_with('secret')
        self.assertTrue(receipt['fresh_quotes_published']);self.assertTrue(board['partial_board'])
        self.assertEqual(board['board_offers'][0]['observed_at'],NOW.isoformat())
        self.assertEqual(receipt['remaining_credits_header'],'0')
        self.assertNotIn('topup_balance',receipt)

    def test_failed_http_has_no_retry_or_board_and_consumes_claim(self):
        import urllib.error
        _,schedule=fixture();claimed=recovery.claim(PRIOR,NOW,'run')
        reader=Mock(side_effect=urllib.error.HTTPError('url',429,'SECRET',{},None))
        receipt,board=recovery.execute(claimed,schedule,NOW,'run','secret',reader,clock=lambda:NOW)
        self.assertIsNone(board);reader.assert_called_once();self.assertEqual(receipt['http_status'],429)
        self.assertNotIn('SECRET',json.dumps(receipt))
        with self.assertRaises(ValueError):recovery.claim(receipt,NOW,'second')

    def test_stale_empty_future_demo_wrong_fixture_or_cost_preserves_prior(self):
        for mode in ('stale','empty','future','demo','wrong_fixture','cost','tier'):
            page,schedule=fixture();usage={'charged_credits':'10'}
            if mode=='stale':page['data'][0]['observed_at']=(NOW-dt.timedelta(minutes=61)).isoformat()
            if mode=='future':page['data'][0]['observed_at']=(NOW+dt.timedelta(seconds=1)).isoformat()
            if mode=='empty':page['data']=[]
            if mode=='demo':page['meta']['mode']='demo'
            if mode=='wrong_fixture':schedule['games']=[]
            if mode=='cost':usage['charged_credits']='41'
            if mode=='tier':page['data'][0]['tier']='demon'
            receipt,board=recovery.execute(recovery.claim(PRIOR,NOW,'run'),schedule,NOW,'run','secret',Mock(return_value=(page,usage)),clock=lambda:NOW)
            self.assertIsNone(board,mode);self.assertFalse(receipt['fresh_quotes_published'],mode)

    def test_wrong_claim_or_expiry_never_calls_provider(self):
        for claimed,when in (({},NOW),(recovery.claim(PRIOR,NOW,'other'),NOW),(recovery.claim(PRIOR,NOW,'run'),recovery.END)):
            reader=Mock()
            with self.assertRaises(ValueError):recovery.execute(claimed,{},when,'run','secret',reader,clock=lambda:NOW)
            reader.assert_not_called()

    def test_response_time_used_and_post_tip_response_rejected(self):
        page,schedule=fixture(); claimed=recovery.claim(PRIOR,NOW,'run')
        later=NOW+dt.timedelta(seconds=20)
        receipt,board=recovery.execute(claimed,schedule,NOW,'run','secret',
            Mock(return_value=(page,{})),clock=lambda:later)
        self.assertEqual(board['generated_at'],later.isoformat())
        self.assertNotIn('charged_credits',receipt)
        receipt,board=recovery.execute(claimed,schedule,NOW,'run','secret',
            Mock(return_value=(page,{})),clock=lambda:recovery.END)
        self.assertIsNone(board);self.assertFalse(receipt['fresh_quotes_published'])

    def test_exact_one_time_push_trigger(self):
        request={'authorization_id':recovery.AUTHORIZATION,
            'action':'EXECUTE_SINGLE_AUTHORIZED_COMPACT_READ','requested_at':NOW.isoformat()}
        event={'ref':'refs/heads/main','before':'a'*40,'after':'b'*40,'commits':[{'id':'b'*40}]}
        recovery.authorize_trigger('push','refs/heads/main','1',NOW,request,event,[recovery.REQUEST_PATH])
        recovery.authorize_trigger('workflow_dispatch','refs/heads/main','1',NOW)
        cases=[('push','refs/heads/main','1',NOW,None,event),
            ('push','refs/heads/main','1',NOW,{**request,'authorization_id':'other'},event),
            ('push','refs/heads/main','1',NOW,request,{'ref':'refs/heads/main','commits':[{'modified':['.github/workflows/nba-prizepicks-one-time-recovery.yml']}]}),
            ('push','refs/heads/main','1',NOW,request,{**event,'deleted':True}),
            ('push','refs/heads/other','1',NOW,request,event),
            ('schedule','refs/heads/main','1',NOW,request,event),
            ('push','refs/heads/main','1',NOW,{**request,'requested_at':(NOW+dt.timedelta(seconds=1)).isoformat()},event),
            ('push','refs/heads/main','1',NOW,{**request,'requested_at':(recovery.START-dt.timedelta(seconds=1)).isoformat()},event),
            ('push','refs/heads/main','1',recovery.END,request,event)]
        for args in cases:
            with self.assertRaises(ValueError):recovery.authorize_trigger(*args,changed_paths=() if args[5].get('commits')==[{'modified':['.github/workflows/nba-prizepicks-one-time-recovery.yml']}] else [recovery.REQUEST_PATH])

    def test_push_diff_uses_verified_sha_range(self):
        from unittest.mock import patch
        event={'before':'a'*40,'after':'b'*40}
        with patch.object(recovery.subprocess,'check_output',return_value=recovery.REQUEST_PATH+'\n') as git:
            self.assertEqual(recovery.changed_request_paths(event,'b'*40),[recovery.REQUEST_PATH])
            self.assertEqual(git.call_args.args[0],['git','diff','--name-only','--diff-filter=AM','a'*40,'b'*40,'--',recovery.REQUEST_PATH])
            with self.assertRaises(ValueError):recovery.changed_request_paths(event,'c'*40)

    def test_workflow_manual_only_pinned_and_preclaim_before_call(self):
        root=Path(__file__).resolve().parents[2]
        text=(root/'.github/workflows/nba-prizepicks-one-time-recovery.yml').read_text()
        self.assertIn('workflow_dispatch:',text)
        for forbidden in ('  schedule:', '  pull_request:'):
            self.assertNotIn(forbidden,text)
        self.assertIn('    branches: [main]\n    paths:\n      - docs/prizepicks_one_time_recovery_request.json\npermissions:', text)
        self.assertIn('group: nba-independent-prizepicks-feed',text)
        self.assertLess(text.index('git push origin HEAD:main'),text.index('one_time_prizepicks_recovery fetch'))
        self.assertIn("always() && steps.claim.outputs.claimed == 'true'",text)
        self.assertNotIn('fetch_prizepicks.py',text)
        import re
        for action in re.findall(r'uses: (\S+)',text):self.assertRegex(action,r'@[0-9a-f]{40}$')

if __name__=='__main__':unittest.main()

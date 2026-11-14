import unittest,json,urllib.error
from iphone_bot.probe_tennis_provider import probe,summary,URL,category

class Reply:
    headers={'X-Credits-Cost':'3','X-Credits-Remaining':'70'}
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):return json.dumps(self.payload).encode()

class ProbeTest(unittest.TestCase):
    def payload(self):
        return {'meta':{'mode':'live','source_status':'fresh','next_cursor':'more'},'data':[{'league':'TENNIS','player':{'id':'1','name':'Real Name'},'event':{'starts_at':'2026-11-15T00:00:00Z','opponent':'Opponent'},'market':{'stat':'Total Games'},'source_fields':{}}]}
    def test_only_one_call_and_credit_record(self):
        calls=[]
        def open(req,timeout):calls.append(req);return Reply(self.payload())
        result,raw=probe('test-only-placeholder',open)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0].full_url,URL)
        self.assertEqual(result['credits_cost'],3)
        self.assertTrue(result['has_next_page'])
        self.assertFalse(result['complete_board_claimed'])
        self.assertNotIn('Real Name',json.dumps(result))
        self.assertNotIn('test-only-placeholder',json.dumps(result))
        self.assertFalse(result['shapes'][0]['has_surface'])
    def test_missing_key_no_call(self):
        result,raw=probe('',lambda *_:self.fail('called without key'))
        self.assertEqual(result['status'],'MISSING_GITHUB_SECRET')
    def test_demo_wrong_league_and_excess_rows_rejected(self):
        p=self.payload();p['meta']['mode']='demo'
        with self.assertRaises(ValueError):summary(p)
        p=self.payload();p['data'][0]['league']='NBA'
        with self.assertRaises(ValueError):summary(p)
        p=self.payload();p['data']*=101
        with self.assertRaises(ValueError):summary(p)
    def test_http_error_never_retried(self):
        calls=[]
        def open(req,timeout):calls.append(1);raise urllib.error.HTTPError(URL,429,'',{},None)
        result,raw=probe('test-only-placeholder',open)
        self.assertEqual(calls,[1]);self.assertEqual(result['http_status'],429)
        self.assertIsNone(raw)

    def test_malformed_metadata_rejected(self):
        p=self.payload();p['meta']='bad'
        with self.assertRaises(ValueError):summary(p)
    def test_main_requires_durable_claim_and_attempt_token(self):
        import tempfile,os
        from pathlib import Path
        from unittest.mock import patch
        from iphone_bot import probe_tennis_provider as module
        with tempfile.TemporaryDirectory() as folder:
            req=Path(folder)/'request.json';out=Path(folder)/'status.json'
            req.write_text(json.dumps({'request_id':'one'}))
            with patch.object(module,'REQUEST',req),patch.object(module,'OUTPUT',out),patch.object(module,'probe') as call:
                with patch.dict(os.environ,{'TENNIS_PROBE_CLAIM':'run-2'}):
                    module.main();call.assert_not_called()
                    out.write_text(json.dumps({'request_id':'one','status':'CLAIMED_NO_RETRY','claim_token':'run-1'}))
                    module.main();call.assert_not_called()
                    out.write_text(json.dumps({'request_id':'one','status':'PROBE_COMPLETE','claim_token':'run-2'}))
                    module.main();call.assert_not_called()

    def test_minimized_in_product_quote(self):
        from iphone_bot.probe_tennis_provider import normalized_board
        p=self.payload();r=p['data'][0]
        r.update(id='q1',fixture_id='f1',status='active',is_demo=False,line=22.5,observed_at='2026-11-14T19:59:00Z',selections=[{'side':x,'available':True,'tier':'standard'} for x in ['more','less']])
        r['market']['period']='Full game';r['source_fields']['projection_type']='Single Stat'
        r['secret_unexpected']='do-not-publish'
        out=normalized_board(p,'2026-11-14T20:00:00+00:00')
        self.assertEqual(out['accepted_quote_count'],1)
        self.assertEqual(out['quotes'][0]['line'],22.5)
        self.assertFalse(out['quotes'][0]['is_combo'])
        self.assertNotIn('secret_unexpected',json.dumps(out))
        r['market']['period']='1st Set'
        self.assertEqual(normalized_board(p,'2026-11-14T20:00:00+00:00')['accepted_quote_count'],0)

    def test_normalized_input_boundaries(self):
        from iphone_bot.probe_tennis_provider import normalized_board
        p=self.payload();r=p['data'][0]
        r.update(id='q1',fixture_id='f1',status='active',is_demo=False,line=22.5,observed_at='2026-11-14T19:59:00Z',selections=[{'side':x,'available':True,'tier':'standard'} for x in ['more','less']])
        r['market']['period']='Full game';r['source_fields']['projection_type']='Single Stat'
        now='2026-11-14T20:00:00+00:00'
        r['is_combo']=True
        self.assertEqual(normalized_board(p,now)['accepted_quote_count'],0)
        del r['is_combo'];r['player']['name']={'unexpected':'nested'}
        self.assertEqual(normalized_board(p,now)['accepted_quote_count'],0)
        r['player']['name']='Valid Name';r['fixture_id']=['nested']
        self.assertEqual(normalized_board(p,now)['accepted_quote_count'],0)
        r['fixture_id']='f1';del p['meta']['next_cursor']
        self.assertFalse(normalized_board(p,now)['complete_pagination'])

class ProbeDiagnosticsTest(unittest.TestCase):
    def payload(self):
        return {'meta':{'mode':'live','source_status':'fresh','next_cursor':None},'data':[{
            'id':'q1','fixture_id':'f1','league':'TENNIS','status':'active',
            'player':{'id':'p1','name':'Not included in diagnostics'},
            'event':{'starts_at':'2026-11-15T00:00:00Z','opponent':'Private opponent'},
            'market':{'stat':'Total Games','period':'Full match'},
            'source_fields':{'projection_type':'Single Stat'},'line':22.5,
            'observed_at':'2026-11-14T20:00:01Z',
            'selections':[{'side':s,'available':True,'tier':'standard'} for s in ['more','less']]}]}
    def test_receipt_time_accepts_observation_during_request(self):
        from unittest.mock import patch
        from iphone_bot import probe_tennis_provider as module
        with patch.object(module,'utc_now',side_effect=['2026-11-14T20:00:00+00:00','2026-11-14T20:00:02+00:00']):
            result,payload=module.probe('test-only-placeholder',lambda *a,**k:Reply(self.payload()))
        self.assertEqual(result['checked_at'],result['response_received_at'])
        self.assertNotEqual(result['request_started_at'],result['response_received_at'])
        board=module.normalized_board(payload,result['response_received_at'])
        self.assertEqual(board['accepted_quote_count'],1)
        self.assertEqual(board['quotes'][0]['captured_at'],result['response_received_at'])
        self.assertEqual(module.normalized_board(payload,result['request_started_at'])['rejection_counts'],{'OBSERVED_AFTER_RECEIPT':1})
    def test_rejection_counts_are_fixed_labels_and_account_every_row(self):
        import copy
        from iphone_bot.probe_tennis_provider import normalized_board
        p=self.payload();base=p['data'][0]
        rejected=[]
        for field,value in [('line',float('nan')),('status','closed'),('is_combo',True),('selections',[])]:
            row=copy.deepcopy(base);row[field]=value;rejected.append(row)
        row=copy.deepcopy(base);del row['event']['starts_at'];rejected.append(row)
        row=copy.deepcopy(base);row['market']['period']='First Set';rejected.append(row)
        row=copy.deepcopy(base);row['source_fields']['projection_type']='unknown';rejected.append(row)
        p['data']+=rejected
        board=normalized_board(p,'2026-11-14T20:00:02+00:00')
        self.assertEqual(board['accepted_quote_count'],1)
        self.assertEqual(board['rejected_quote_count'],7)
        self.assertEqual(sum(board['rejection_counts'].values()),7)
        self.assertEqual(board['rejection_counts']['MISSING_OR_MALFORMED_FIELDS'],1)
        diagnostics=json.dumps(board['rejection_counts'])
        for private in ['Not included','Private opponent','q1','f1','p1']:
            self.assertNotIn(private,diagnostics)
    def test_metadata_presence_not_values_and_stale_provider_count(self):
        from iphone_bot.probe_tennis_provider import normalized_board,summary
        p=self.payload();del p['meta']['next_cursor']
        self.assertEqual(summary(p)['metadata_present'],{'mode':True,'source_status':True,'next_cursor':False})
        p['meta']['source_status']='stale'
        board=normalized_board(p,'2026-11-14T20:00:02+00:00')
        self.assertEqual(board['rejection_counts'],{'PROVIDER_NOT_FRESH_LIVE':1})
        self.assertEqual(board['accepted_quote_count'],0)

class CategorySafetyTest(unittest.TestCase):
    def test_categories_never_retain_unknown_values(self):
        for value in ["private name", {}, [], 42]:
            self.assertEqual(category(value,{"full"}),"OTHER")
        self.assertEqual(category(None,{"full"}),"MISSING")
        self.assertEqual(category("full",{"full"}),"full")

    def test_conflicting_duplicates_and_same_opponent_withheld(self):
        from iphone_bot.probe_tennis_provider import normalized_board
        payload=ProbeTest().payload();r=payload['data'][0]
        r.update(id='q1',fixture_id='f1',status='active',is_demo=False,line=22.5,observed_at='2026-11-14T19:59:00Z',selections=[{'side':x,'available':True,'tier':'standard'} for x in ['more','less']])
        r['market']['period']='Full game';r['source_fields']['projection_type']='Single Stat'
        r['selections'].append({'side':'more','available':False,'tier':'standard'})
        now='2026-11-14T20:00:00+00:00'
        self.assertEqual(normalized_board(payload,now)['rejection_counts'],{'DUPLICATE_SELECTION_SIDE':1})
        r['selections'].pop();r['event']['opponent']=' '+r['player']['name'].swapcase()+' '
        self.assertEqual(normalized_board(payload,now)['rejection_counts'],{'EXPLICIT_IDENTITY_CONFLICT':1})

    def test_malformed_market_rejected_before_telemetry(self):
        payload=ProbeTest().payload();payload['data'][0]['market']='unexpected'
        with self.assertRaises(ValueError):summary(payload)

class ExplicitSelectionTests(unittest.TestCase):
    def board(self,selections,**updates):
        from iphone_bot.probe_tennis_provider import normalized_board
        payload=ProbeDiagnosticsTest().payload()
        payload['data'][0].update(selections=selections,**updates)
        return normalized_board(payload,'2026-11-14T20:00:02+00:00')
    def test_one_side_does_not_invent_other_side(self):
        for side,other in [('more','less'),('less','more')]:
            board=self.board([dict(side=side,available=True,tier='standard')])
            self.assertEqual(board['accepted_quote_count'],1)
            q=board['quotes'][0]
            self.assertTrue(q[side+'_available']);self.assertEqual(q[side+'_tier'],'standard')
            self.assertIsNone(q[other+'_available']);self.assertIsNone(q[other+'_tier'])
    def test_mixed_side_evidence_is_preserved(self):
        for available in [True,False,None,'true',1]:
            for tier in ['demon','goblin','unknown',None,'unsupported']:
                with self.subTest(available=available,tier=tier):
                    q=self.board([dict(side='more',available=True,tier='standard'),
                                  dict(side='less',available=available,tier=tier)])['quotes'][0]
                    self.assertIs(q['less_available'],available if isinstance(available,bool) else None)
                    self.assertEqual(q['less_tier'],tier if tier in ('demon','goblin','unknown') else None)
    def test_no_explicit_available_standard_side_rejected(self):
        for available,tier in [(False,'standard'),(None,'standard'),('true','standard'),(1,'standard'),(True,'demon'),(True,'goblin'),(True,'unknown'),(True,None)]:
            out=self.board([dict(side='more',available=available,tier=tier)])
            self.assertEqual(out['rejection_counts'],{'NO_AVAILABLE_STANDARD_SIDE':1})
        self.assertEqual(self.board([])['rejection_counts'],{'NO_AVAILABLE_STANDARD_SIDE':1})
    def test_duplicate_or_malformed_sides_rejected(self):
        side=dict(side='more',available=True,tier='standard')
        self.assertEqual(self.board([side,side])['rejection_counts'],{'DUPLICATE_SELECTION_SIDE':1})
        for selections in [None,{},[side,None],[side,dict(side='other')]]:
            self.assertEqual(self.board(selections)['rejection_counts'],{'MALFORMED_SELECTIONS':1})
    def test_fantasy_score_exact_market_only(self):
        from iphone_bot.probe_tennis_provider import normalized_board
        p=ProbeDiagnosticsTest().payload();r=p['data'][0]
        r['source_fields']['projection_type']='Fantasy Score'
        self.assertEqual(normalized_board(p,'2026-11-14T20:00:02+00:00')['rejection_counts'],{'SINGLE_STAT_OR_FANTASY_SCORE_UNVERIFIED':1})
        r['market']['stat']='Fantasy Score'
        out=normalized_board(p,'2026-11-14T20:00:02+00:00')
        self.assertEqual(out['accepted_quote_count'],1)
        self.assertNotIn('projection',out['quotes'][0]);self.assertNotIn('probability',out['quotes'][0])
    def test_combo_event_and_self_opponent_rejected(self):
        from iphone_bot.probe_tennis_provider import normalized_board
        for location in ['root','event','source_fields']:
            for key,value in [('event_type','combo'),('is_combo',True)]:
                p=ProbeDiagnosticsTest().payload();r=p['data'][0]
                (r if location=='root' else r[location])[key]=value
                self.assertEqual(normalized_board(p,'2026-11-14T20:00:02+00:00')['rejection_counts'],{'LIVE_PROMO_OR_COMBO':1})
        p=ProbeDiagnosticsTest().payload();r=p['data'][0];r['event']['opponent']=' '+r['player']['name'].upper()+' '
        self.assertEqual(normalized_board(p,'2026-11-14T20:00:02+00:00')['rejection_counts'],{'EXPLICIT_IDENTITY_CONFLICT':1})

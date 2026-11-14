import unittest,json,urllib.error
from iphone_bot.probe_tennis_provider import probe,summary,URL

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

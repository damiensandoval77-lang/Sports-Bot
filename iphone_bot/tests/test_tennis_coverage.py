import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from iphone_bot import probe_tennis_coverage as p

class CoverageTests(unittest.TestCase):
    def test_echo_refused(self):
        with self.assertRaises(ValueError): p.safe({'unexpected':'secret'},'secret')
    def test_redirect_refused(self):
        with self.assertRaises(ValueError): p.NoRedirect().redirect_request(None,None,None,None,None,None)
    def test_oversize(self):
        with self.assertRaises(ValueError): p.safe('x'*1000001,'key')
    def run_probe(self, opener):
        with tempfile.TemporaryDirectory() as d:
            old=os.getcwd(); os.chdir(d)
            try:
                with patch.dict(os.environ,{'PRIZEPICKS_API_KEY':'secret'}),patch.object(p.urllib.request,'build_opener',return_value=opener):p.main()
                return json.loads(Path('tennis-coverage-status.json').read_text())
            finally:os.chdir(old)
    def test_single_fixed_request(self):
        op=MagicMock();r=op.open.return_value.__enter__.return_value
        r.read.return_value=b'{"meta":{"leagues_graded":["TENNIS"]}}';r.status=200;r.headers={'X-Credits-Cost':'0'}
        out=self.run_probe(op)
        op.open.assert_called_once();self.assertEqual(op.open.call_args.args[0].full_url,p.URL)
        self.assertEqual(out['credits_cost'],'0');self.assertFalse(out['live_ready'])
    def test_header_echo_never_output(self):
        op=MagicMock();r=op.open.return_value.__enter__.return_value
        r.read.return_value=b'{}';r.status=200;r.headers={'X-Credits-Cost':'secret'}
        out=self.run_probe(op);self.assertNotIn('secret',json.dumps(out))
        self.assertEqual(out['credits_cost'],'UNVERIFIED')
    def test_error_no_retry_no_secret(self):
        op=MagicMock();op.open.side_effect=ValueError('secret')
        out=self.run_probe(op);op.open.assert_called_once();self.assertNotIn('secret',json.dumps(out))
    def test_missing_key_no_request(self):
        with patch.dict(os.environ,{'PRIZEPICKS_API_KEY':''}),patch.object(p.urllib.request,'build_opener') as op:
            with self.assertRaises(SystemExit):p.main()
            op.assert_not_called()
if __name__=='__main__':unittest.main()

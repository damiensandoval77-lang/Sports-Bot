"""Synthetic local-boundary checks; no provider or production data requests."""
import copy
import json
import tempfile
import unittest
from src.sports.tennis.provenance import capture_quote, write_receipt, supplied_result_outcome


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.now='2026-11-14T20:00:00Z'
        self.quote=dict(id='q1',player_id='p1',opponent_player_id='p2',fixture_id='f1',
                        player='Synthetic One',opponent='Synthetic Two',stat='Total Games',line=20,
                        period='full_match',status='active',is_demo=False,is_combo=False,tier='standard',
                        more_available=True,more_tier='standard',less_available=None,less_tier=None,
                        observed_at='2026-11-14T19:59:00Z',captured_at=self.now,
                        starts_at='2026-11-14T21:00:00Z')
        self.board=dict(schema_version='tennis_board_v1',source='independent_prizepicksapi_com',
                        source_status='fresh',provider_mode='live',is_demo=False,
                        generated_at=self.now,quotes=[self.quote])
        self.result=dict(source='independent_prizepicksapi_com',source_url='https://example.org/results/f1',
                         fixture_id='f1',player_ids=['p2','p1'],verified_result=True,status='completed',
                         retired=False,walkover=False,score='6-4 6-4',
                         completed_at='2026-11-14T23:00:00Z',observed_at='2026-11-14T23:01:00Z')
    def capture(self):
        return capture_quote(self.board,self.quote,source_url='https://example.org/quote/q1',as_of=self.now)
    def settle(self,receipt=None):
        return supplied_result_outcome(receipt or self.capture(),self.result,as_of='2026-11-14T23:02:00Z')
    def test_minimal_stable_receipt_preserves_unknown_side(self):
        self.quote.update(forecast=99,hit_probability=.99,unexpected={'raw':'private'})
        envelope=self.capture();r=envelope['receipt']
        self.assertEqual(envelope,self.capture())
        self.assertEqual(r['sides']['less'],{'available':None,'tier':None})
        for forbidden in ['forecast','hit_probability','unexpected']:
            self.assertNotIn(forbidden,r)
    def test_post_start_stale_future_and_naive_rejected(self):
        for key,value in [('captured_at','2026-11-14T21:00:00Z'),
                          ('observed_at','2026-11-14T19:00:00Z'),
                          ('observed_at','2026-11-14T20:00:01Z'),
                          ('observed_at','2026-11-14T19:59:00')]:
            with self.subTest(key=key,value=value):
                old=self.quote[key];self.quote[key]=value
                with self.assertRaises(ValueError):self.capture()
                self.quote[key]=old
        self.now='2026-11-14T21:00:00Z'
        with self.assertRaises(ValueError):self.capture()
    def test_false_unknown_or_nonstandard_only_sides_rejected(self):
        for available,tier in [(False,'standard'),(None,'standard'),('true','standard'),(True,'demon')]:
            self.quote.update(more_available=available,more_tier=tier)
            with self.assertRaises(ValueError):self.capture()
    def test_append_only_and_hash_tamper(self):
        receipt=self.capture()
        with tempfile.TemporaryDirectory() as folder:
            path=write_receipt(receipt,folder)
            self.assertEqual(write_receipt(receipt,folder),path)
            damaged=copy.deepcopy(receipt);damaged['receipt']['line']=5
            with self.assertRaises(ValueError):write_receipt(damaged,folder)
            with self.assertRaises(ValueError):self.settle(damaged)
            path.write_text('conflicting data')
            with self.assertRaises(ValueError):write_receipt(receipt,folder)
    def test_descriptive_outcome_never_model_hit_rate(self):
        for line,outcome in [(19.5,'OVER'),(20,'PUSH'),(20.5,'UNDER')]:
            self.quote['line']=line;r=self.settle()
            self.assertEqual(r['line_outcome'],outcome)
            self.assertFalse(r['live_ready']);self.assertFalse(r['model_pick_issued'])
            self.assertIsNone(r['model_win']);self.assertIsNone(r['model_hit_rate'])
            self.assertEqual(r['evidence_status'],'unverified_supplied_result')
    def test_missing_opponent_can_capture_but_cannot_settle(self):
        del self.quote['opponent_player_id']
        receipt=self.capture()
        with self.assertRaises(ValueError):self.settle(receipt)
    def test_exact_identity_required(self):
        for key,value in [('fixture_id','other'),('player_ids',['p1','other']),
                          ('player_ids',['p1','p1']),('source','another_provider')]:
            old=self.result[key];self.result[key]=value
            with self.assertRaises(ValueError):self.settle()
            self.result[key]=old
    def test_result_status_score_and_chronology_guards(self):
        for key,value in [('retired',True),('walkover',True),('retired',None),
                          ('status','in_progress'),('verified_result',False),
                          ('score','6-4 RET'),('score','6-4 3-1'),
                          ('completed_at','2026-11-14T20:30:00Z'),
                          ('observed_at','2026-11-14T22:59:00Z'),
                          ('observed_at','2026-11-14T23:03:00Z'),('source_url','http://example.org')]:
            old=self.result[key];self.result[key]=value
            with self.assertRaises(ValueError):self.settle()
            self.result[key]=old
    def test_unsupported_markets_never_graded(self):
        for stat in ['Total Games Won','Aces','Fantasy Score','Double Faults']:
            self.quote['stat']=stat
            with self.assertRaises(ValueError):self.settle()

if __name__=='__main__':unittest.main()

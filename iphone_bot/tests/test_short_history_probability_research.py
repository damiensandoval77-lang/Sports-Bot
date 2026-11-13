import unittest
from copy import deepcopy
from unittest.mock import patch
import numpy as np
from iphone_bot.short_history_probability_research import probability,merge,settle,capture,MODEL,STATUS

NOW='2026-11-13T23:00:00+00:00'
def row():
 return {'receipt_key':'test','candidate_model':MODEL,'player_id':'1','team':'AAA','game':'A @ B','start':'2026-11-14T00:00:00+00:00','stat':'PTS','line':10.,'market_updated':'2026-11-13T22:50:00+00:00','captured_at':NOW,'archived_at':NOW,'research_probability_over':.4,'research_probability_under':.5,'research_probability_push':.1,'primary_model_eligible':False,'official_grade_eligible':False,'calibrated':False,'historical_improvement_gate_passed':False}
def final(actual=11.):
 return {**row(),'actual':actual,'grade':'HIT','grade_source':'NBA_CDN_FINAL','source_game_id':'0022600001'}
class Tests(unittest.TestCase):
 def test_integer_push(self):
  p=probability([10,4,2],np.zeros((1000,3)),10,0);np.testing.assert_equal(p,[0,0,1])
 def test_half_line(self):
  p=probability([10,4,2],np.zeros((1000,3)),9.5,0);np.testing.assert_equal(p,[1,0,0])
 def test_joint_pra(self):
  p=probability([10,4,2],np.zeros((1000,3)),16,3);np.testing.assert_equal(p,[0,0,1])
 def test_negative_draw_clamped(self):
  p=probability([0,0,0],-np.ones((1000,3)),0,0);np.testing.assert_equal(p,[0,0,1])
 def test_invalid_distribution(self):
  for r in [np.zeros((999,3)),np.zeros((1000,2)),np.full((1000,3),np.nan)]:
   with self.assertRaises(ValueError):probability([1,1,1],r,1,0)
 def test_first_wins(self):
  a=merge(None,{'records':[row()]},NOW);b=row();b['research_probability_over']=.5;b['research_probability_under']=.4
  self.assertEqual(merge(a,{'records':[b]},NOW)['records'],a['records'])
 def test_posttip_rejected(self):
  with self.assertRaises(ValueError):merge(None,{'records':[row()]},'2026-11-14T00:00:00+00:00')
 def test_stale_rejected(self):
  with self.assertRaises(ValueError):merge(None,{'records':[row()]},'2026-11-13T23:31:00+00:00')
 def test_invalid_probabilities(self):
  for val in [float('nan'),-.1,1.1,True]:
   r=row();r['research_probability_over']=val
   with self.assertRaises(ValueError):merge(None,{'records':[r]},NOW)
 def test_primary_rejected(self):
  r=row();r['primary_model_eligible']=True
  with self.assertRaises(ValueError):merge(None,{'records':[r]},NOW)
 def test_settlement_separate(self):
  a=merge(None,{'records':[row()]},NOW);b=settle(a,[final()], '2026-11-14T03:00:00+00:00')
  self.assertEqual(a['records'],b['records']);self.assertEqual(b['outcomes']['test']['result'],'OVER');self.assertEqual(a['outcomes'],{})
 def test_final_conflict_rejected(self):
  a=merge(None,{'records':[row()]},NOW);b=settle(a,[final()], '2026-11-14T03:00:00+00:00')
  with self.assertRaises(ValueError):settle(b,[final(9)], '2026-11-14T03:10:00+00:00')
 def test_ambiguous_final_withheld(self):
  a=merge(None,{'records':[row()]},NOW);b=settle(a,[final(),final(9)], '2026-11-14T03:00:00+00:00');self.assertEqual(b['outcomes'],{})
 def test_unverified_final_ignored(self):
  a=merge(None,{'records':[row()]},NOW);f=final();f['grade_source']='CSV'
  self.assertEqual(settle(a,[f], '2026-11-14T03:00:00+00:00')['outcomes'],{})
 def test_void_and_unsettled_ignored(self):
  a=merge(None,{'records':[row()]},NOW)
  for grade in ['VOID','DNP','UNSETTLED_RESEARCH',None]:
   f=final();f['grade']=grade
   self.assertEqual(settle(a,[f],'2026-11-14T03:00:00+00:00')['outcomes'],{})
 def test_pretip_final_ignored(self):
  a=merge(None,{'records':[row()]},NOW);self.assertEqual(settle(a,[final()],NOW)['outcomes'],{})
 def test_push_result(self):
  a=merge(None,{'records':[row()]},NOW);self.assertEqual(settle(a,[final(10)],'2026-11-14T03:00:00+00:00')['outcomes']['test']['result'],'PUSH')
class CaptureTests(unittest.TestCase):
 def test_candidate_provenance_and_prior_cutoff(self):
  class Model:
   def __init__(self,v):self.v=v
   def predict(self,x):return np.array([self.v]*len(x))
  class Map:
   def predict(self,x):return np.array(x)
  eligible={**row(),'player':'Test','player_id':'1','team':'AAA','opponent':'BBB','projection':3.,'prior_games':3,'history_dates':['2026-11-01','2026-11-02','2026-11-03'],'source':'INDEPENDENTLY_CROSSCHECKED_PLAYER_HISTORY','pickem_tier':'standard','standard_line_two_sided_verified':True,'research_only':True}
  rs=[{'id':'1','team':'AAA','date':d,'PTS':3.,'REB':2.,'AST':1.,'MIN':20.,'FGA':5.,'FTA':1.,'TOV':1.} for d in eligible['history_dates']]
  rs.append({**rs[0],'date':'2026-11-13','PTS':999.})
  ctx={t:[('2026-11-01',{'poss':90.},{'PTS':100.,'poss':90.})]*3 for t in ['AAA','BBB']}
  pack={'models':[Model(10),Model(4),Model(2)],'residuals':np.zeros((1000,3)),'maps':{s:Map() for s in ['PTS','REB','AST','PRA']},'baseline_residuals':np.zeros((1000,3)),'baseline_maps':{s:Map() for s in ['PTS','REB','AST','PRA']},'artifact_sha256':'a'*64,'spec_sha256':'b'*64,'source_hashes':[],'library_versions':{}}
  with patch('iphone_bot.short_history_probability_research.eligibility',return_value={'estimates':[eligible]}),patch('iphone_bot.short_history_probability_research.build_team_games',return_value=ctx):
   a=capture(rs,{},pack,primary={},injuries={},news={},free_watch={},now=NOW)['records'][0]
   self.assertEqual(a['candidate_projection'],10.);self.assertEqual(a['descriptive_baseline_projection'],3.)
   self.assertEqual(a['features']['PTS_mean'],3.);self.assertEqual(a['line'],10.)
   self.assertEqual(a['baseline_probability_under'],1.);self.assertEqual(a['research_probability_push'],1.);self.assertIsNone(a['research_half_integer_calibrated_map_over'])
   self.assertEqual(a['method'],MODEL);self.assertTrue(a['trained_model']);self.assertFalse(a['primary_model_eligible'])
   pack['artifact_sha256']='c'*64
   b=capture(rs,{},pack,primary={},injuries={},news={},free_watch={},now=NOW)['records'][0]
   self.assertNotEqual(a['receipt_key'],b['receipt_key'])
 def test_old_quote_rejected_despite_new_capture(self):
  r=row();r['market_updated']='2026-11-13T22:29:59+00:00'
  with self.assertRaises(ValueError):merge(None,{'records':[r]},NOW)
if __name__=='__main__':unittest.main()

import unittest,json,tempfile
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import numpy as np
from iphone_bot import short_history_direct_capture as c
NOW='2026-11-14T20:00:00+00:00'
class Classifier:
 def predict_proba(self,x):return np.array([[.4,.6] for _ in x])
class Mapping:
 def predict(self,x):return np.array(x)
def pack():return dict(models={s:Classifier() for s in ('PTS','REB','AST','PRA')},maps={s:Mapping() for s in ('PTS','REB','AST','PRA')},baseline_maps={s:Mapping() for s in ('PTS','REB','AST','PRA')},baseline_residuals=np.zeros((1000,3)),threshold_grid={'PTS':[4.5,29.5],'REB':[1.5,9.5],'AST':[.5,8.5],'PRA':[9.5,39.5]})
def row():return dict(receipt_key='first',candidate_model=c.MODEL,player_id='1',player='Test',team='A',opponent='B',game='A @ B',stat='PTS',line=10.5,projection=9.,prior_games=3,history_dates=['2026-11-01','2026-11-02','2026-11-03'],start='2026-11-15T00:00:00+00:00',market_updated='2026-11-14T19:50:00+00:00',captured_at=NOW,archived_at=NOW,research_probability_over=.6,research_probability_under=.4,research_probability_push=0.,baseline_probability_over=.5,baseline_probability_under=.5,baseline_probability_push=0.,primary_model_eligible=False,official_grade_eligible=False,calibrated=False)
class Tests(unittest.TestCase):
 def test_integer_or_extrapolation_never_inferred(self):
  for line in (10,0.5,30.5,float('nan'),True):
   with self.assertRaises(ValueError):c.predict(pack(),'PTS',line,{k:1. for k in c.FEATURES})
 def test_probabilities_valid(self):
  raw,p,b=c.predict(pack(),'PTS',10.5,{k:1. for k in c.FEATURES});self.assertEqual(p,.6);self.assertEqual(b,0.)
 def test_nonfinite_feature_rejected(self):
  with self.assertRaises(ValueError):c.predict(pack(),'PTS',10.5,{k:float('nan') for k in c.FEATURES})
 def test_archive_distinct_and_idempotent(self):
  a=c.merge(None,{'records':[row()]},NOW);self.assertEqual(a,c.merge(a,{'records':[row()]},NOW));self.assertEqual(a['status'],c.STATUS)
  with self.assertRaises(ValueError):c.merge({'status':'UNVALIDATED_SHORT_HISTORY_PROBABILITY_RESEARCH','records':[]},{'records':[]},NOW)
 def test_original_receipts_and_outcomes_immutable(self):
  a=c.merge(None,{'records':[row()]},NOW);a['outcomes']={'first':{'actual':11}};r=row();r['captured_at']='2026-11-14T20:01:00+00:00';r['archived_at']=r['captured_at'];r['research_probability_over']=.7;r['research_probability_under']=.3
  b=c.merge(a,{'records':[r]},r['captured_at']);self.assertEqual(a,b)
 def test_conflicting_tie_rejected(self):
  r=row();r['research_probability_over']=.7;r['research_probability_under']=.3
  for rows in ([row(),r],[r,row()]):
   with self.assertRaises(ValueError):c.merge(None,{'records':rows},NOW)
 def test_posttip_late_archive_stale_rejected(self):
  for field,value in [('archived_at','2026-11-15T01:00:00+00:00'),('market_updated','2026-11-14T19:00:00+00:00')]:
   r=row();r[field]=value
   with self.assertRaises(ValueError):c.merge(None,{'records':[r]},NOW)
 def test_primary_or_bad_probability_rejected(self):
  for field,value in [('primary_model_eligible',True),('research_probability_over',float('nan')),('line',10)]:
   r=row();r[field]=value
   with self.assertRaises(ValueError):c.merge(None,{'records':[r]},NOW)
 def test_artifact_load_real_and_tampering(self):
  p,m=c.load_bundle();self.assertEqual(p['model'],c.MODEL)
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);(path/'manifest.json').write_text(json.dumps(m));(path/'model.joblib').write_bytes(b'corrupt')
   with self.assertRaisesRegex(ValueError,'ARTIFACT_HASH'):c.load_bundle(path)
   m['versions']['numpy']='wrong';(path/'manifest.json').write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'PROVENANCE'):c.load_bundle(path)
 def test_capture_distinct_and_no_ui_projection(self):
  r=row();base=dict(estimates=[r],excluded={});manifest=dict(spec_sha256='s',artifact_sha256='a',code_sha256={},versions={},source_hashes=[])
  with patch.object(c,'eligible',return_value=base),patch.object(c,'build_team_games',return_value={}),patch.object(c,'features',return_value=({k:1. for k in c.FEATURES},None)),patch.object(c,'capture_context',return_value={'official_report':{'verified_at_capture':True}}):
   out=c.capture([],{},pack(),manifest,primary={},injuries={},news={},free_watch={},now=NOW)
   self.assertEqual(len(out['records']),1);self.assertIsNone(out['records'][0]['projection']);self.assertFalse(out['records'][0]['primary_model_eligible']);self.assertEqual(r,row())
 def test_injury_source_guard(self):
  with patch.object(c,'eligible',return_value=dict(estimates=[row()],excluded={})),patch.object(c,'build_team_games',return_value={}),patch.object(c,'capture_context',return_value={'official_report':{'verified_at_capture':False}}):
   out=c.capture([],{},pack(),{},primary={},injuries={},news={},free_watch={},now=NOW);self.assertEqual(out['records'],[])
if __name__=='__main__':unittest.main()

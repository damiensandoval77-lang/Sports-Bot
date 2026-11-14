import unittest,json
from copy import deepcopy
from datetime import datetime
from iphone_bot import nba_confidence_calibration as c
NOW=datetime.fromisoformat('2026-11-14T21:00:00+00:00')
def row():return dict(player_id='1',player='Test',team='A',opponent='B',game='A @ B',start='2026-11-15T00:00:00+00:00',stat='PTS',line=9.5,projection=12.,captured_at='2026-11-14T20:00:00+00:00',market_updated='2026-11-14T19:59:00+00:00',pickem_tier='standard',standard_line_two_sided_verified=True,grade='PENDING',opponent_context_unavailable=False,single_source_history=False,injury_uncertainty_unresolved=False,opponent_adjustment_verified=True,estimated_hit_chance=dict(method='JOINT_2024_25_VALIDATION_RESIDUALS_20K_UNCALIBRATED',draws=20000,calibrated=False,market='PTS',modeled_more_probability=.8,modeled_less_probability=.2,modeled_push_probability=0.,modeled_direction='More',modeled_selected_probability=.8))
def source(rows=None):return dict(status='FROZEN_NEW_AI_ALL_MARKET',records=rows or [row()])
class Tests(unittest.TestCase):
 def test_fixed_formula_and_original_side_retained(self):
  out=c.build(source(),now=NOW);r=out['records'][0];self.assertLess(r['corrected_original_side_probability'],.8);self.assertEqual(r['original_side'],'MORE');self.assertEqual(r['raw_estimated_hit_chance'],row()['estimated_hit_chance'])
 def test_source_immutable(self):
  s=source();before=deepcopy(s);c.build(s,now=NOW);self.assertEqual(s,before)
 def test_previous_receipts_immutable(self):
  a=c.build(source(),now=NOW);b=c.build(source(),a,datetime.fromisoformat('2026-11-14T21:30:00+00:00'));self.assertEqual(a['records'],b['records'])
 def test_no_after_tip_backfill(self):
  self.assertEqual(c.build(source(),now=datetime.fromisoformat('2026-11-15T01:00:00+00:00'))['records'],[])
 def test_existing_pretip_receipt_retained_after_tip(self):
  a=c.build(source(),now=NOW);b=c.build(source(),a,datetime.fromisoformat('2026-11-15T01:00:00+00:00'));self.assertEqual(a['records'],b['records'])
 def test_other_model_not_transferred(self):
  r=row();r['estimated_hit_chance']['method']='POSITION_V_POSITION_DEF_RATING_RESEARCH_ANALYTIC_V1';self.assertEqual(c.build(source([r]),now=NOW)['records'],[])
 def test_integer_push_context_and_graded_withheld(self):
  for field,value in [('line',10),('single_source_history',True),('injury_uncertainty_unresolved',True),('opponent_context_unavailable',True),('grade','GRADED'),('captured_at','2026-11-15T00:01:00+00:00')]:
   r=row();r[field]=value;self.assertEqual(c.build(source([r]),now=NOW)['records'],[])
 def test_bad_distributions(self):
  for field,value in [('modeled_more_probability',float('nan')),('modeled_push_probability',.1),('modeled_selected_probability',.9),('draws',100)]:
   r=row();r['estimated_hit_chance'][field]=value;self.assertEqual(c.build(source([r]),now=NOW)['records'],[])
 def test_ambiguous_source_fails_closed(self):
  r=row();r['projection']=13.;self.assertEqual(c.build(source([row(),r]),now=NOW)['records'],[])
 def test_original_more_can_be_below_half_without_flipping_pick(self):
  r=row();r['estimated_hit_chance'].update(modeled_more_probability=.55,modeled_less_probability=.45,modeled_selected_probability=.55)
  o=c.build(source([r]),now=NOW)['records'][0];self.assertEqual(o['original_side'],'MORE');self.assertLess(o['corrected_original_side_probability'],.5)
if __name__=='__main__':unittest.main()

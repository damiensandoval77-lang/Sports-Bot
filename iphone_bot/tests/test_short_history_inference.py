import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from copy import deepcopy
from iphone_bot.short_history_inference import estimates
from iphone_bot.short_history_candidate import MODEL,FEATURES,TRAIN,VALIDATE

class Model:
    def predict(self,x):return [12.25]

def fixture():
    pack={'model':MODEL,'features':FEATURES,'training_seasons':TRAIN,'validation_season':VALIDATE,
        'research_only':True,'calibrated':False,'primary_model_eligible':False,
        'accepted_markets':{'PTS':True,'REB':True,'AST':False,'PRA':False},
        'models':{s:Model() for s in ('PTS','REB','AST')}}
    v={s:{'n':2000,'dates':100,'model_mae':4.,'date_clustered_difference_ci95':[-.2,-.1] if s in ('PTS','REB') else [-.1,.1]} for s in ('PTS','REB','AST','PRA')}
    report={'model':MODEL,'library_versions':{'sklearn':__import__('sklearn').__version__},'status':'SHORT_HISTORY_RETROSPECTIVE_VALIDATION','validation':v,
            'diagnostic':{s:{'n':2000,'mae_difference':-.1} for s in v}}
    row={'player':'Fixture','player_id':'123','team':'BOS','opponent':'NYK',
         'start':'2026-11-13T00:00:00Z','stat':'PTS','projection':9.,'line':10.5}
    base={'estimates':[row],'excluded':{},'official_report_issued_at':'2026-11-12T22:30:00Z'}
    return pack,report,base

class InferenceTests(unittest.TestCase):
    def call(self,pack,report,base):
        with patch('iphone_bot.short_history_inference.eligible',return_value=base),\
             patch('iphone_bot.short_history_inference.build_team_games',return_value={}),\
             patch('iphone_bot.short_history_inference.features',return_value=({k:1. for k in FEATURES},None)):
            return estimates([],{},pack,report,primary={},now=datetime(2026,11,12,23,tzinfo=timezone.utc))
    def test_separate_model_not_promoted_baseline(self):
        p,r,b=fixture();before=deepcopy(b);out=self.call(p,r,b)
        self.assertEqual(out['estimates'][0]['projection'],12.25)
        self.assertEqual(out['estimates'][0]['descriptive_baseline_projection'],9.)
        self.assertEqual(b,before)
        self.assertFalse(out['primary_model_eligible']);self.assertFalse(out['official_grade_eligible'])
        self.assertIsNone(out['estimates'][0]['hit_probability'])
        self.assertFalse(out['prospective_validation_verified'])
    def test_nonfinite_model_output_never_becomes_zero(self):
        for value in (float('nan'),float('inf')):
            p,r,b=fixture()
            p['models']['PTS']=type('Bad',(),{'predict':lambda self,x:[value]})()
            self.assertEqual(self.call(p,r,b)['count'],0)
    def test_failed_market_gate_cannot_be_overridden_by_flag(self):
        p,r,b=fixture();p['accepted_markets']['PRA']=True;b['estimates'][0]['stat']='PRA'
        self.assertEqual(self.call(p,r,b)['count'],0)
    def test_wrong_training_or_calibration_claim_rejected(self):
        for field,value in [('calibrated',True),('primary_model_eligible',True),('training_seasons',['2025-26'])]:
            p,r,b=fixture();p[field]=value
            with self.assertRaises(ValueError):self.call(p,r,b)
    def test_eligibility_block_remains_explicit(self):
        p,r,b=fixture();b['estimates']=[];b['blocker']='INJURY_CONTEXT_UNVERIFIED_OR_STALE'
        out=self.call(p,r,b);self.assertEqual(out['count'],0);self.assertEqual(out['blocker'],b['blocker'])



class ArtifactAndPublicationTests(unittest.TestCase):
    def test_stale_and_future_history_fail(self):
        from iphone_bot.short_history_inference import check_history_freshness
        now=datetime(2026,11,12,23,tzinfo=timezone.utc)
        for day in ('2026-11-01','2026-11-13'):
            with self.assertRaises(ValueError):check_history_freshness({'latest_game_date':day},now)
        check_history_freshness({'latest_game_date':'2026-11-11'},now)
    def test_error_clears_previous_output(self):
        import tempfile,json
        from pathlib import Path
        from iphone_bot.short_history_inference import publish_current
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'old.json';out.write_text('{"estimates":[{"stale":true}]}')
            with patch('iphone_bot.short_history_inference.build_current',side_effect=ValueError('stale')):
                r=publish_current(Path(d),Path(d),out)
            self.assertEqual(r['count'],0);self.assertIn('blocker',r)
            self.assertEqual(json.loads(out.read_text())['estimates'],[])
    def test_bound_model_and_report_must_both_match(self):
        import tempfile,json
        from pathlib import Path
        from iphone_bot.short_history_candidate import save_artifacts
        from iphone_bot.short_history_inference import load_verified_artifacts
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);p,r,_=fixture();save_artifacts(p,r,directory)
            loaded,_=load_verified_artifacts(directory);self.assertEqual(loaded['model'],MODEL)
            report=json.loads((directory/'validation.json').read_text());report['validation']['PTS']['n']=9999
            (directory/'validation.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'REPORT_HASH'):load_verified_artifacts(directory)
            save_artifacts(p,r,directory);(directory/'short_history_candidate.joblib').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'ARTIFACT_HASH'):load_verified_artifacts(directory)

if __name__=='__main__':unittest.main()

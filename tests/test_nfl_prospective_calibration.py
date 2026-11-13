import copy,json,unittest
from scripts.audit_nfl_prospective_calibration import build

class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.schedule={'games':[{'game_id':'g','home':'NYG','away':'WAS','status':'final','kickoff_utc':'2026-11-13T01:15:00Z'}]}
        self.e=dict(schema='NFL_OPPONENT_FEATURES_V2',captured_at='2026-11-13T01:00:00Z',observed_at='2026-11-13T00:59:00Z',game_id='g',player_id='p',team='WAS',opponent='NYG',target='REC',original_line=3.,direction='MORE',artifact_sha256='a'*64,model_id='m',modeled_more_probability=.6,modeled_less_probability=.25,modeled_push_probability=.15,selected_probability=.6)
        self.r=dict(odds_type='standard',grade_status='graded',captured_at=self.e['captured_at'],game_id='g',player_id='p',team='WAS',opponent='NYG',target='REC',line='3',actual='4',pick='More',result='More',won='1',position='WR')
    def run_report(self,changes=None,evidence=None):
        r=dict(self.r);r.update(changes or {});r['matchup_evidence']=json.dumps(evidence or self.e)
        return build([r],self.schedule)
    def test_real_line_win_and_no_calibration_claim(self):
        x=self.run_report();self.assertEqual(x['summary']['wins'],1);self.assertAlmostEqual(x['summary']['brier_unconditional'],.16);self.assertFalse(x['calibrated'])
    def test_push_is_not_win_and_not_settled(self):
        x=self.run_report({'actual':'3','result':'Push','won':''})['summary'];self.assertEqual(x['pushes'],1);self.assertIsNone(x['settled_hit_rate']);self.assertAlmostEqual(x['brier_unconditional'],.36)
    def test_postgame_evidence_rejected(self):
        e=dict(self.e,captured_at='2026-11-13T01:16:00Z');x=self.run_report({'captured_at':e['captured_at']},e);self.assertEqual(x['excluded'],{'not_pregame':1})
    def test_identity_line_selected_side_rejected(self):
        for changes,reason in [({'player_id':'other'},'identity_mismatch'),({'line':'9'},'line_or_actual_invalid'),({'pick':'Less'},'direction_mismatch')]:
            self.assertEqual(self.run_report(changes)['excluded'],{reason:1})
    def test_missing_evidence_cannot_use_model_pct(self):
        r=dict(self.r,model_pct='99',matchup_evidence='');self.assertEqual(build([r],self.schedule)['summary']['rows'],0)
    def test_legacy_integer_excluded_half_line_allowed(self):
        e=dict(self.e,schema='NFL_OPPONENT_FEATURES_V1');self.assertEqual(self.run_report(evidence=e)['excluded'],{'legacy_integer_push_unknown':1})
        e['original_line']=3.5;self.assertEqual(self.run_report({'line':'3.5'},e)['summary']['rows'],1)
    def test_bad_outcome_and_distribution_rejected(self):
        self.assertEqual(self.run_report({'won':'0'})['excluded'],{'grade_mismatch':1})
        self.assertEqual(self.run_report(evidence=dict(self.e,modeled_push_probability=.5))['excluded'],{'invalid_distribution':1})
    def test_duplicate_rejected(self):
        r=dict(self.r,matchup_evidence=json.dumps(self.e))
        with self.assertRaises(ValueError):build([r,r],self.schedule)
    def test_alternative_and_unfinal_excluded(self):
        self.assertEqual(self.run_report({'odds_type':'demon'})['summary']['rows'],0)
        self.schedule['games'][0]['status']='in_progress';self.assertEqual(self.run_report()['summary']['rows'],0)
    def test_role_provenance_only(self):
        self.assertIn('legacy_support_unknown',self.run_report()['by']['role'])
        self.assertIn('returner_uncertain',self.run_report(evidence=dict(self.e,eligibility_context={'playing_time_uncertain':True}))['by']['role'])
    def test_input_not_mutated(self):
        r=dict(self.r,matchup_evidence=json.dumps(self.e));old=copy.deepcopy(r);build([r],self.schedule);self.assertEqual(r,old)
if __name__=='__main__':unittest.main()

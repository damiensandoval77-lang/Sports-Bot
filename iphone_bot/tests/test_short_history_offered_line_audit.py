import unittest
from copy import deepcopy
from iphone_bot.short_history_offered_line_audit import audit

def fixture():
    r=dict(player_id='1',team='A',opponent='B',game='A @ B',stat='PTS',line=10.5,
        archived_at='2026-11-13T23:30:00Z',start='2026-11-14T00:00:00Z',captured_at='2026-11-13T23:00:00Z',market_updated='2026-11-13T22:59:00Z',history_dates=['2026-11-10'],
        pickem_tier='standard',standard_line_two_sided_verified=True,primary_model_eligible=False,
        candidate_model='fixed',spec_sha256='s',artifact_sha256='a',receipt_key='first')
    for prefix,p in [('research',.7),('baseline',.5)]:
        r.update({prefix+'_probability_over':p,prefix+'_probability_under':1-p,prefix+'_probability_push':0.,prefix+'_half_integer_calibrated_map_over':p})
    outcome=dict(actual=11.,source='NBA_CDN_FINAL',source_game_id='g',observed_at='2026-11-14T03:00:00Z',result='OVER')
    return dict(records=[r],outcomes={'first':outcome})

class AuditTests(unittest.TestCase):
    def test_known_brier(self):
        x=audit(fixture());self.assertAlmostEqual(x['cohorts'][0]['three_way_brier'],.18);self.assertIsNone(x['cohorts'][0]['date_cluster_ci95']);self.assertFalse(x['primary_release_eligible'])
    def test_duplicate_capture_does_not_inflate(self):
        x=fixture();r=deepcopy(x['records'][0]);r.update(captured_at='2026-11-13T23:10:00Z',receipt_key='later');x['records'].append(r)
        self.assertEqual(audit(x)['selected_offers'],1)
    def test_no_outcome_based_selection(self):
        x=fixture();r=deepcopy(x['records'][0]);r.update(captured_at='2026-11-13T23:10:00Z',receipt_key='later');x['records'].append(r);x['outcomes']={'later':x['outcomes']['first']}
        result=audit(x);self.assertEqual(result['pending'],1);self.assertEqual(result['cohorts'],[])
    def test_posttip_rejected(self):
        x=fixture();x['records'][0]['captured_at']=x['records'][0]['start'];self.assertEqual(audit(x)['selected_offers'],0)
    def test_push_uses_three_way_distribution(self):
        x=fixture();r=x['records'][0];r['line']=10
        for prefix in ('research','baseline'):
            r.update({prefix+'_probability_over':.4,prefix+'_probability_under':.4,prefix+'_probability_push':.2})
        x['outcomes']['first'].update(actual=10,result='PUSH');z=audit(x)['cohorts'][0];self.assertAlmostEqual(z['three_way_brier'],.96);self.assertEqual(z['scoring'],'raw_three_way')
    def test_bad_sum_rejected(self):
        x=fixture();x['records'][0]['research_probability_push']=.5;self.assertEqual(audit(x)['cohorts'],[])
    def test_conflicting_outcome_rejected(self):
        x=fixture();x['outcomes']['first']['result']='UNDER';self.assertEqual(audit(x)['cohorts'],[])
    def test_missing_or_posttip_archive_rejected(self):
        for value in (None, '2026-11-14T00:01:00Z', '2026-11-13T22:00:00Z'):
            x=fixture();x['records'][0]['archived_at']=value
            self.assertEqual(audit(x)['cohorts'],[])
    def test_conflicting_earliest_receipts_rejected_in_both_orders(self):
        x=fixture();r=deepcopy(x['records'][0]);r['research_probability_over']=.1;r['research_probability_under']=.9;r['research_half_integer_calibrated_map_over']=.1
        x['records'].append(r)
        for rows in (x['records'],list(reversed(x['records']))):
            result=audit(dict(x,records=rows));self.assertEqual(result['cohorts'],[]);self.assertEqual(result['rejected']['CONFLICTING_EARLIEST_RECEIPTS'],1)
    def test_identical_duplicate_receipts_collapse(self):
        x=fixture();x['records'].append(deepcopy(x['records'][0]));self.assertEqual(audit(x)['cohorts'][0]['offers'],1)
    def test_later_conflict_does_not_poison_earlier_receipt(self):
        x=fixture();r=deepcopy(x['records'][0]);r['captured_at']='2026-11-13T23:10:00Z';other=deepcopy(r);other['research_probability_over']=.9
        x['records']=[r,other,*x['records']];self.assertEqual(audit(x)['cohorts'][0]['offers'],1)
    def test_versions_separate(self):
        x=fixture();r=deepcopy(x['records'][0]);r.update(artifact_sha256='new',receipt_key='new');x['records'].append(r);x['outcomes']['new']=x['outcomes']['first'];self.assertEqual(len(audit(x)['cohorts']),2)

if __name__=='__main__':unittest.main()

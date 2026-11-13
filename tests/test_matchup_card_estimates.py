import copy
import unittest
from datetime import datetime, timezone
from research.build_matchup_card_estimates import build, EXPECTED, POLICY, METHOD, STATUS, PROVENANCE

NOW = datetime(2026,11,12,20,tzinfo=timezone.utc)
def inputs():
    row = dict(player_id='1',player='Real Player',team='AAA',opponent='BBB',stat='PTS',line=10.5,start='2026-11-13T00:00:00+00:00',captured_at='2026-11-12T19:00:00+00:00',original_side='MORE',original_projection=11,matchup_projection=12,observed_as_prospective=True,research_snapshot_captured_at='2026-11-12T19:01:00+00:00',source_run_id='run',estimated_hit_chance=dict(method=METHOD,calibrated=False,research_only=True,verified_betting_edge=False,opponent_aware_inputs_sourced=True,opponent_adjustment_validated=False,modeled_selected_probability=.6,source_provenance={k:'2026-11-12T17:00:00+00:00' for k in PROVENANCE}))
    p={**row,'captured_at':'2026-11-12T18:00:00+00:00','market_updated':'2026-11-12T17:59:00+00:00','projection':11,'pickem_tier':'standard','standard_line_two_sided_verified':True,'research_only':True,'production_replaced':False,'estimated_hit_chance':{'modeled_direction':'More'}}
    ledger={'status':'FROZEN_NEW_AI_ALL_MARKET','records':[p]}
    archive={'status':STATUS,'version':1,'forecasts':[row]}
    current={'status':EXPECTED,'calibrated':False,'production_approved':False,'presentation_policy':POLICY,'captured_at':row['research_snapshot_captured_at'],'model_id':'run','records':[]}
    return ledger,archive,current

class MatchupCardEstimatesTests(unittest.TestCase):
    def test_recovers_exact_archived_observation_without_recalculating(self):
        l,a,c=inputs(); result=build(l,a,c,NOW)
        assert result['records']==a['forecasts']
        assert result['captured_at']==a['forecasts'][0]['research_snapshot_captured_at']
        assert result['records'][0]['captured_at']!=l['records'][0]['captured_at']

    def test_identical_duplicate_deduplicates_conflict_excluded(self):
        l,a,c=inputs();c['records']=[copy.deepcopy(a['forecasts'][0])]
        assert len(build(l,a,c,NOW)['records'])==1
        c['records'][0]['estimated_hit_chance']['modeled_selected_probability']=.9
        assert build(l,a,c,NOW)['records']==[]
        assert build(l,a,c,NOW)['conflicting_observations_excluded']==1

    def test_rejects_wrong_identity_future_provenance_and_nonprospective(self):
        for field,value in [('line',11.5),('original_side','LESS'),('team','CCC'),('opponent','CCC'),('stat','AST'),('start','2026-11-14T00:00:00+00:00'),('observed_as_prospective',False),('captured_at','2026-11-12T17:00:00+00:00'),('research_snapshot_captured_at','2026-11-13T00:00:00+00:00'),('research_snapshot_captured_at','2026-11-12T18:30:00+00:00')]:
            l,a,c=inputs();a['forecasts'][0][field]=value
            assert build(l,a,c,NOW)['records']==[],field
        l,a,c=inputs();a['forecasts'][0]['estimated_hit_chance']['source_provenance']['minutes_snapshot_at']='2026-11-12T19:02:00+00:00'
        assert build(l,a,c,NOW)['records']==[]

    def test_latest_capture_selected_preserves_probability(self):
        l,a,c=inputs(); row=copy.deepcopy(a['forecasts'][0]);row['captured_at']='2026-11-12T19:30:00+00:00';row['research_snapshot_captured_at']='2026-11-12T19:31:00+00:00';row['estimated_hit_chance']['modeled_selected_probability']=.65;a['forecasts'].append(row)
        assert build(l,a,c,NOW)['records']==[row]

    def test_stale_slate_excluded_and_empty_valid(self):
        l,a,c=inputs();assert build(l,a,c,datetime(2026,11,20,tzinfo=timezone.utc))['records']==[]

    def test_invalid_wrapper_and_primary_bounds(self):
        for value in ("invalid", "2026-11-12T21:00:00+00:00"):
            l,a,c=inputs();c["captured_at"]=value
            with self.assertRaises(ValueError): build(l,a,c,NOW)
        for field,value in (("pickem_tier","goblin"),("projection",float("nan")),("projection",-1),("line",0)):
            l,a,c=inputs();l["records"][0][field]=value
            self.assertEqual(build(l,a,c,NOW)["records"],[])

    def test_malformed_rows_do_not_suppress_good_recovery(self):
        l,a,c=inputs()
        good=copy.deepcopy(a['forecasts'][0])
        a['forecasts'].extend([None, [], 'invalid'])
        c['records'].extend([None, [], 'invalid'])
        for value in (None, [], 'invalid'):
            bad=copy.deepcopy(good);bad['estimated_hit_chance']=value
            a['forecasts'].append(bad)
            bad=copy.deepcopy(good);bad['estimated_hit_chance']['source_provenance']=value
            a['forecasts'].append(bad)
        self.assertEqual(build(l,a,c,NOW)['records'], [good])
        c['records']=None
        with self.assertRaises(ValueError): build(l,a,c,NOW)

if __name__ == "__main__":
    unittest.main()

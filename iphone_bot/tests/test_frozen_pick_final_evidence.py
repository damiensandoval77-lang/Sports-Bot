import copy
import unittest
from iphone_bot.frozen_pick_final_evidence import augment_final_evidence
from iphone_bot.multimarket_forecast_ledger import merge
from iphone_bot.published_pick_settlement import evaluate

class CachedFrozenEvidenceTests(unittest.TestCase):
    def setUp(self):
        p={'player_id':'1630567','player':'Scottie Barnes','team':'TOR',
           'game':'New York Knicks @ Toronto Raptors','start':'2026-11-15T23:00:00+00:00',
           'stat':'PTS','line':17.5,'projection':20.,'market_updated':'2026-11-15T21:50:00+00:00',
           'captured_at':'2026-11-15T21:56:14+00:00','pickem_tier':'standard',
           'standard_line_two_sided_verified':True,'research_only':True,
           'calibrated_probability':None,'estimated_hit_chance':{'modeled_direction':'More'},'grade':'PENDING'}
        self.ledger={'status':'FROZEN_NEW_AI_ALL_MARKET','records':[p]}
        self.row={'player':'Scottie Barnes','nba_person_id':'1630567','team':'TOR','opponent':'NYK',
                  'date':'2026-11-15','PTS':30.,'REB':9.,'AST':4.,'PRA':43.,'MIN':36.3167,
                  'source':'NBA_CDN_FINAL','source_game_id':'0022600241','final_confirmed':True}
    def test_cache_only_pick_grades_and_audits_without_fabricated_forecast(self):
        before=copy.deepcopy(self.ledger)
        finals=augment_final_evidence({},self.ledger,[self.row])
        self.assertNotIn('projection',finals['records'][0])
        result=merge(self.ledger,{},finals)
        self.assertEqual(result['records'][0]['actual'],30)
        self.assertEqual(result['records'][0]['line'],17.5)
        self.assertEqual(result['records'][0]['projection'],20)
        self.assertEqual(evaluate(result,finals)['status'],'READY')
        self.assertEqual(self.ledger,before)
    def test_wrong_identity_date_opponent_unconfirmed_or_bad_sum_rejected(self):
        for field,value in [('nba_person_id','1'),('team','NYK'),('opponent','BOS'),
                            ('date','2026-11-17'),('final_confirmed',False),('PRA',44),
                            ('source','LIVE'),('source_game_id','bad'),('MIN',0)]:
            with self.subTest(field=field):
                self.assertEqual(augment_final_evidence({},self.ledger,[{**self.row,field:value}])['records'],[])
    def test_conflicting_cache_rejected(self):
        bad={**self.row,'PTS':31,'PRA':44}
        self.assertEqual(augment_final_evidence({},self.ledger,[self.row,bad])['records'],[])
    def test_existing_outcome_never_overwritten(self):
        old=augment_final_evidence({},self.ledger,[self.row])
        self.assertEqual(augment_final_evidence(old,self.ledger,[{**self.row,'PTS':31,'PRA':44}]),old)
    def test_each_frozen_line_can_use_one_final(self):
        self.ledger['records'].append({**self.ledger['records'][0],'line':22.5})
        finals=augment_final_evidence({},self.ledger,[self.row])
        self.assertEqual(len(finals['records']),1)
        self.assertEqual(merge(self.ledger,{},finals)['new_verified_grades'],2)
    def test_dnp_is_not_inferred(self):
        self.assertEqual(augment_final_evidence({},self.ledger,[{**self.row,'dnp_final_verified':True,'dnp_reason':'Coach'}])['records'],[])

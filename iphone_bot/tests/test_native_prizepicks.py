import copy
import datetime as dt
import unittest
from unittest.mock import patch
from iphone_bot.fetch_native_prizepicks import build
from iphone_bot.publish_prizepicks_site import summarize
from iphone_bot.build_prizepicks_model_input import convert
from iphone_bot.validate_prizepicks_publish import validate
from iphone_bot.archive_prizepicks_pregame_lines import build as archive
from iphone_bot.prizepicks_provenance import NATIVE
NOW=dt.datetime(2026,11,14,20,tzinfo=dt.timezone.utc)
SCHEDULE={'games':[{'game':'Brooklyn Nets @ Milwaukee Bucks','start':'2026-11-15T01:00:00+00:00'}]}
def fixture():
    return {'meta':{'current_page':1,'total_pages':1},'included':[
        {'type':'new_player','id':'1','attributes':{'name':'Test Player','team':'BKN','league':'NBA','combo':False}},
        {'type':'duration','id':'11','attributes':{'name':'Full'}}],
        'data':[{'type':'projection','id':'123','attributes':{'odds_type':'standard','allowed_wager_types':'under_or_over',
            'status':'pre_game','is_live':False,'in_game':False,'is_promo':False,'stat_type':'Points',
            'start_time':'2026-11-15T01:00:00Z','line_score':20.5,'description':'MIL'},
            'relationships':{'new_player':{'data':{'type':'new_player','id':'1'}},
                             'duration':{'data':{'type':'duration','id':'11'}}}}]}
class NativeQuotes(unittest.TestCase):
    def test_real_source_survives_export_model_and_immutable_archive(self):
        raw=build(fixture(),SCHEDULE,NOW.isoformat());site,health=summarize(raw,SCHEDULE)
        model=convert(site,now=NOW)
        self.assertEqual([],validate(raw,site,model,now=NOW))
        self.assertEqual(NATIVE,site['source']);self.assertEqual(2,len(model['picks']))
        self.assertTrue(all(x['source']==NATIVE for x in model['picks']))
        saved=archive(site,now=NOW);self.assertEqual(1,saved['count'])
        later=copy.deepcopy(site);later['generated_at']=(NOW+dt.timedelta(minutes=5)).isoformat()
        later['board_offers'][0]['observed_at']=later['generated_at']
        self.assertEqual(saved['quotes'],archive(later,saved,now=NOW+dt.timedelta(minutes=5))['quotes'])
        self.assertFalse(health['provider_board_fully_paged'])
    def test_rejects_unverified_rows(self):
        for key,val in [('odds_type','demon'),('odds_type','goblin'),('allowed_wager_types','over'),
                        ('allowed_wager_types',None),('is_live',True),('is_promo',True),('in_game',True),
                        ('status','in_progress'),('stat_type','Fantasy Score'),('line_score',float('nan')),
                        ('line_score',True),('description','LAL'),('start_time','2026-11-14T19:00:00Z')]:
            with self.subTest(key=key,val=val):
                p=fixture();p['data'][0]['attributes'][key]=val
                with self.assertRaises(ValueError):build(p,SCHEDULE,NOW.isoformat())
    def test_rejects_combo_partial_and_ambiguous(self):
        for scenario in ['combo','half','page','ambiguous','conflicting']:
            with self.subTest(scenario=scenario):
                p=fixture();s=copy.deepcopy(SCHEDULE)
                if scenario=='combo':p['included'][0]['attributes']['combo']=True
                if scenario=='half':p['included'][1]['attributes']['name']='1H'
                if scenario=='page':p['meta']['total_pages']=2
                if scenario=='ambiguous':s['games']*=2
                if scenario=='conflicting':
                    q=copy.deepcopy(p['data'][0]);q['id']='456';q['attributes']['line_score']=21.5;p['data'].append(q)
                with self.assertRaises(ValueError):build(p,s,NOW.isoformat())
    def test_wrong_provider_label_rejected(self):
        raw=build(fixture(),SCHEDULE,NOW.isoformat());site,_=summarize(raw,SCHEDULE);model=convert(site,now=NOW)
        site['source']='independent_prizepicksapi_com'
        self.assertIn('INVALID_SITE_SOURCE',validate(raw,site,model,now=NOW))
    def test_observed_time_is_request_time_not_provider_update(self):
        p=fixture();p['data'][0]['attributes']['updated_at']='2026-11-10T00:00:00Z'
        q=build(p,SCHEDULE,NOW.isoformat())['board_offers'][0]
        self.assertEqual(NOW.isoformat(),q['observed_at'])
        self.assertEqual('2026-11-10T00:00:00Z',q['provider_updated_at'])
if __name__=='__main__':unittest.main()

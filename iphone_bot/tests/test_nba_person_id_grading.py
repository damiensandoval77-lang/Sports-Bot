import unittest
from iphone_bot.grade_frozen_ai_forecasts import settle_predictions
from iphone_bot.verified_final_cache import merge_rows
from test_grade_frozen_ai_forecasts import forecast,final

class NbaPersonIdTests(unittest.TestCase):
    def test_exact_official_id_allows_name_variant(self):
        r={**final('Different display name'),'nba_person_id':forecast()['player_id']}
        self.assertEqual(settle_predictions([forecast()],[r])['new_grades'],1)

    def test_id_fallback_rejects_wrong_namespace_fixture_and_duplicates(self):
        r={**final('Different display name'),'nba_person_id':forecast()['player_id']}
        for changes in [{'source':'ESPN_FINAL'},{'team':'DEN'},{'opponent':'DAL'},
                        {'date':'2026-11-09'},{'nba_person_id':'999'}, {'final_confirmed':False}]:
            self.assertEqual(settle_predictions([forecast()],[{**r,**changes}])['new_grades'],0)
        self.assertEqual(settle_predictions([forecast()],[r,{**r,'player':'Other'}])['new_grades'],0)
        dnp={**r,'dnp_final_verified':True,'dnp_reason':'INACTIVE'}
        self.assertEqual(settle_predictions([forecast()],[r,dnp])['new_grades'],0)

    def test_matching_name_with_wrong_id_is_rejected(self):
        self.assertEqual(settle_predictions([forecast()],[{**final(),'nba_person_id':'999'}])['new_grades'],0)

    def test_cache_enrichment_is_not_stat_overwrite(self):
        r=final(); tagged={**r,'nba_person_id':'1642846'}
        self.assertEqual(merge_rows([r],[tagged]),[tagged])
        self.assertEqual(merge_rows([tagged],[r]),[tagged])
        self.assertEqual(merge_rows([tagged],[{**tagged,'nba_person_id':'999'}]),[])
        self.assertEqual(merge_rows([r],[{**tagged,'MIN':25}]),[])

    def test_name_and_id_conflicts_fail_closed(self):
        idrow={**final('Alias'),'nba_person_id':forecast()['player_id']}
        named={**final(),'source':'ESPN_FINAL'}
        dnp=lambda r:{**r,'dnp_final_verified':True,'dnp_reason':'INACTIVE'}
        for rows in [[named,dnp(idrow)],[dnp(named),idrow],[{**named,'PTS':20},idrow]]:
            result=settle_predictions([forecast()],rows)
            self.assertEqual(result['new_grades'],0)
            self.assertEqual(result['new_exclusions'],0)

    def test_exact_id_dnp_excluded_not_zero_grade(self):
        r={**final('Alias'),'nba_person_id':forecast()['player_id'], 'dnp_final_verified':True,'dnp_reason':'INACTIVE'}
        result=settle_predictions([forecast()],[r])
        self.assertEqual(result['new_exclusions'],1)
        self.assertEqual(result['new_grades'],0)

    def test_parser_retains_official_person_id(self):
        from iphone_bot.fetch_final_boxscores import nba_boxscore_rows
        game={'gameStatus':3,'gameId':'123','gameTimeUTC':'2026-11-09T00:00:00Z',
              'awayTeam':{'teamTricode':'UTA','players':[{'personId':1642846,'name':'Alias','statistics':{'points':19,'reboundsTotal':5,'assists':3,'minutes':'PT27M30S'}}]},
              'homeTeam':{'teamTricode':'MIN','players':[]}}
        rows=nba_boxscore_rows(game,{'game':game})
        self.assertEqual(rows[0]['nba_person_id'],'1642846')

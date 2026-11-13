import unittest
from copy import deepcopy
from iphone_bot.short_history_candidate import features,prepare,FEATURES,TRAIN,VALIDATE,DIAGNOSTIC

def prior(n=3):
    return [{'id':'1','team':'BOS','opponent':'NYK','season':'2024-25','date':f'2024-11-{i+1:02}',
             'PTS':10.,'REB':5.,'AST':3.,'MIN':20.,'FGA':8.,'FTA':2.,'TOV':1.,'OREB':1.} for i in range(n)]
def context():
    box={'poss':100.,'PTS':110.}
    return {team:[(f'2024-11-{i+1:02}',box,box) for i in range(5)] for team in ('BOS','NYK')}

class ShortHistoryTests(unittest.TestCase):
    def test_only_separate_three_to_seven_game_cohort(self):
        for n in (2,8):self.assertEqual(features(prior(n),'BOS','NYK','2024-11-10',context())[1],'OUTSIDE_3_TO_7_GAME_COHORT')
        f,e=features(prior(3),'BOS','NYK','2024-11-10',context())
        self.assertIsNone(e);self.assertEqual(f['history_count'],3)
        self.assertEqual(set(f),set(FEATURES))
    def test_same_day_future_and_other_team_do_not_leak(self):
        rows=prior();expected=features(rows,'BOS','NYK','2024-11-10',context())
        rows += [{**rows[0],'date':'2024-11-10','PTS':999.},{**rows[0],'date':'2024-11-11','PTS':999.},{**rows[0],'team':'DAL','PTS':999.}]
        self.assertEqual(features(rows,'BOS','NYK','2024-11-10',context()),expected)
    def test_duplicate_game_date_fails_closed(self):
        rows=prior()+[prior()[0]]
        self.assertEqual(features(rows,'BOS','NYK','2024-11-10',context())[1],'DUPLICATE_PRIOR_DATE')
    def test_missing_actual_opponent_context_is_not_filled(self):
        self.assertEqual(features(prior(),'BOS','NYK','2024-11-10',{})[1],'INSUFFICIENT_PRIOR_RECIPROCAL_TEAM_CONTEXT')
    def test_target_context_excluded(self):
        expected=features(prior(),'BOS','NYK','2024-11-10',context())
        c=context();c['NYK'].append(('2024-11-10',{'poss':200.},{'PTS':999.,'poss':30.}))
        self.assertEqual(features(prior(),'BOS','NYK','2024-11-10',c),expected)
    def test_bad_minutes_and_nonfinite_values_rejected(self):
        for k,v in [('MIN',0.),('PTS',float('nan')),('AST',-1.)]:
            rows=prior();rows[0][k]=v
            self.assertIsNotNone(features(rows,'BOS','NYK','2024-11-10',context())[1])
    def test_chronological_season_partitions_are_disjoint(self):
        self.assertEqual(TRAIN,('2022-23','2023-24'))
        self.assertNotIn(VALIDATE,TRAIN);self.assertNotIn(DIAGNOSTIC,TRAIN)

if __name__=='__main__':unittest.main()

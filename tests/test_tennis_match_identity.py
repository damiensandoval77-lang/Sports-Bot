import unittest
import pandas as pd
from src.sports.tennis.features import add_opponent_features, add_opponent_surface_context
from src.sports.tennis.builder import expand_to_player_rows

class MatchIdentityTests(unittest.TestCase):
    def rows(self):
        return pd.DataFrame([
            dict(tour='atp',tourney_id='x',match_num=m,tourney_date='2026-01-01',player_id=p,opp_id=o,aces_L5=v,aces_hard_L10=v)
            for m,p,o,v in [(1,1,2,10),(1,2,1,20),(2,1,3,11),(2,3,1,30)]
        ])
    def test_no_tournament_cartesian_product(self):
        actual=add_opponent_features(self.rows())
        self.assertEqual(len(actual),4)
        self.assertEqual(actual.opp_aces_L5.tolist(),[20,10,30,11])
    def test_surface_exact_match(self):
        actual=add_opponent_surface_context(self.rows())
        self.assertEqual(actual.opp_aces_hard_L10.tolist(),[20,10,30,11])
    def test_missing_identity_rejected(self):
        with self.assertRaises(ValueError): add_opponent_features(self.rows().drop(columns='match_num'))
    def test_duplicate_rejected(self):
        rows=self.rows()
        with self.assertRaises(ValueError): add_opponent_features(pd.concat([rows,rows.iloc[:1]]))
    def test_other_tour_cannot_cross_match(self):
        a=self.rows(); b=a.copy(); b['tour']='wta'; b['aces_L5']+=100
        result=add_opponent_features(pd.concat([a,b]))
        self.assertEqual(result.opp_aces_L5.tolist(),[20,10,30,11,120,110,130,111])
    def test_builder_preserves_match_num(self):
        rows=expand_to_player_rows(pd.DataFrame([dict(match_num=17,score='6-4 6-3',winner_id=1,loser_id=2)]),'atp')
        self.assertEqual(rows.match_num.tolist(),[17,17])

if __name__=='__main__': unittest.main()

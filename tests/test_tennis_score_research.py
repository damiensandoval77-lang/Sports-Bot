import unittest
import pandas as pd
from src.sports.tennis.score_research import make_features, FEATURES

class ScoreResearchTest(unittest.TestCase):
    def rows(self):
        records=[]
        for i,date in enumerate(['2026-01-01T00:00:00Z','2026-01-01T01:00:00Z','2026-01-05T00:00:00Z']):
            for p,o in [('a','b'),('b','a')]:
                records.append(dict(match_id=str(i),player_id=p,opp_id=o,tour='atp',surface='Hard',match_time_utc=date,total_games=20+i,total_sets=2,total_tiebreaks=0))
        return pd.DataFrame(records)
    def test_no_same_day_or_current_result_leak(self):
        rows=self.rows()
        base=make_features(rows)
        changed=rows.copy()
        changed.loc[changed.match_id=='2','total_games']=99
        result=make_features(changed)
        pd.testing.assert_frame_equal(base[FEATURES],result[FEATURES])
        self.assertEqual(base.iloc[0].history_count,0)
        self.assertEqual(base.iloc[2].history_count,0)
        self.assertEqual(base.iloc[4].total_games_L10,20.5)
    def test_input_order_invariant(self):
        pd.testing.assert_frame_equal(make_features(self.rows()),make_features(self.rows().sample(frac=1,random_state=4)))
    def test_tour_isolated(self):
        rows=self.rows()
        other=rows.copy(); other['tour']='wta'; other['total_games']=90
        result=make_features(pd.concat([rows,other]))
        self.assertEqual(result.query("tour=='atp' and match_id=='2'").iloc[0].total_games_L10,20.5)

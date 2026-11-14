import unittest
import numpy as np
import pandas as pd
from src.sports.tennis.fixture_inference import fixture_features, predict_fixture, CONTRACT
from src.sports.tennis.score_research import FEATURES, make_features

class Stub:
    def predict(self,x):
        assert list(x.columns)==FEATURES
        return [22.5]

class FixtureTest(unittest.TestCase):
    def setUp(self):
        self.now='2026-11-14T20:00:00Z'
        self.fixture=dict(match_id='fixture:1',player_ids=['valuebetennis:1','valuebetennis:2'],
            source_url='https://example.org/fixture/1',observed_at=self.now,
            start_time_utc='2026-11-15T20:00:00Z',status='scheduled',tour='atp',surface='Hard')
        records=[]
        for i,date in enumerate(pd.date_range('2026-10-01',periods=43,tz='UTC')):
            for p,o in [('valuebetennis:1','valuebetennis:2'),('valuebetennis:2','valuebetennis:1')]:
                records.append(dict(match_id=f'old:{i}',player_id=p,opp_id=o,tour='atp',surface='Hard',match_time_utc=date,total_games=20+i%5,total_sets=2,total_tiebreaks=0))
        self.history=pd.DataFrame(records)
        self.bundles={'total_games':dict(model=Stub(),target='total_games',contract=CONTRACT,features=FEATURES,mode='offline_research_only',trained_as_of=self.now)}
    def run_prediction(self):
        return predict_fixture(self.history,self.fixture,self.bundles,as_of=self.now,history_observed_at=self.now)
    def test_research_only_result_no_probabilities(self):
        result=self.run_prediction()
        self.assertEqual(result['projections']['total_games'],22.5)
        self.assertIsNone(result['probabilities'])
        self.assertFalse(result['live_ready'])
    def test_stale_unknown_and_naive_context_rejected(self):
        for field,value in [('observed_at','2026-11-14T18:00:00Z'),('start_time_utc','2026-11-15'),('status','in_progress'),('surface',None),('player_ids',['valuebetennis:1','valuebetennis:999'])]:
            old=self.fixture[field]; self.fixture[field]=value
            with self.assertRaises(ValueError): self.run_prediction()
            self.fixture[field]=old
    def test_incompatible_model_rejected(self):
        self.bundles['total_games']['contract']='legacy'
        with self.assertRaises(ValueError): self.run_prediction()
    def test_future_training_rejected(self):
        self.bundles['total_games']['trained_as_of']='2026-11-16T00:00:00Z'
        with self.assertRaises(ValueError): self.run_prediction()
    def test_no_future_historical_results(self):
        self.history.loc[0,'match_time_utc']=pd.Timestamp('2026-11-18T00:00:00Z')
        with self.assertRaises(ValueError): self.run_prediction()
    def test_training_feature_parity(self):
        fixture=self.fixture
        eligible=self.history[self.history.match_time_utc+pd.Timedelta(days=2)<pd.Timestamp(self.now)].copy()
        upcoming=pd.DataFrame([dict(match_id=fixture['match_id'],player_id=p,opp_id=o,tour='atp',surface='Hard',match_time_utc=pd.Timestamp(fixture['start_time_utc']),total_games=np.nan,total_sets=np.nan,total_tiebreaks=np.nan) for p,o in [fixture['player_ids'],fixture['player_ids'][::-1]]])
        combined=make_features(pd.concat([eligible,upcoming],ignore_index=True))
        expected=combined[(combined.match_id=='fixture:1')&(combined.player_id=='valuebetennis:1')][FEATURES]
        actual=fixture_features(self.history,fixture,as_of=self.now,history_observed_at=self.now)
        pd.testing.assert_frame_equal(expected,actual)
    def test_player_order_invariance(self):
        a=fixture_features(self.history,self.fixture,as_of=self.now,history_observed_at=self.now)
        self.fixture['player_ids'].reverse()
        b=fixture_features(self.history,self.fixture,as_of=self.now,history_observed_at=self.now)
        pd.testing.assert_frame_equal(a,b)

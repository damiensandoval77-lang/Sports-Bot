import unittest
import numpy as np
import pandas as pd
from src.sports.tennis.score_distribution_research import split_three,distribution_metrics,residual_draws

class ScoreDistributionTests(unittest.TestCase):
    def test_whole_day_partitions_and_strict_maturity(self):
        dates=pd.date_range('2026-01-01',periods=100,freq='12h',tz='UTC')
        frame=pd.DataFrame({'match_time_utc':dates})
        train,cal,test,cs,ts=split_three(frame)
        self.assertFalse((train&cal|train&test|cal&test).any())
        self.assertTrue((dates[train]+pd.Timedelta(hours=48)<cs).all())
        self.assertTrue((dates[cal]+pd.Timedelta(hours=48)<ts).all())
        self.assertTrue((dates[cal]>=cs).all());self.assertTrue((dates[test]>=ts).all())
        self.assertTrue((~(train|cal|test)).any())
        self.assertEqual(cs.hour,0);self.assertEqual(ts.hour,0)
        for day in frame.match_time_utc.dt.floor('D').unique():
            positions=np.flatnonzero(frame.match_time_utc.dt.floor('D').to_numpy()==day)
            self.assertFalse(train.iloc[positions].any() and cal.iloc[positions].any())
            self.assertFalse(cal.iloc[positions].any() and test.iloc[positions].any())
    def test_short_history_and_short_lag_rejected(self):
        frame=pd.DataFrame({'match_time_utc':pd.date_range('2026-01-01',periods=5,tz='UTC')})
        with self.assertRaises(ValueError):split_three(frame)
        with self.assertRaises(ValueError):split_three(frame,maturity_hours=0)
    def test_crps_matches_pairwise_formula(self):
        draws=np.array([0,1,3,5])
        out=distribution_metrics(lambda i:draws,[2])
        expected=np.mean(abs(draws-2))-.5*np.mean(abs(draws[:,None]-draws[None,:]))
        self.assertAlmostEqual(out['crps'],expected)
        self.assertEqual(out['coverage_90'],1);self.assertEqual(out['width_90'],5)
    def test_degenerate_exact_forecast_zero_crps(self):
        out=distribution_metrics(lambda i:[20,20],[20])
        self.assertEqual(out['crps'],0);self.assertEqual(out['coverage_50'],1)
    def test_residual_discretization_is_explicit(self):
        np.testing.assert_array_equal(residual_draws(20.2,[-40,0,1.1]),[0,20,21])
        with self.assertRaises(ValueError):residual_draws(20,[])
        with self.assertRaises(ValueError):distribution_metrics(lambda i:[float('nan')],[20])
        with self.assertRaises(ValueError):distribution_metrics(lambda i:[20],[20.5])
    def test_test_outcomes_cannot_change_splits_or_residual_samples(self):
        frame=pd.DataFrame({'match_time_utc':pd.date_range('2026-01-01',periods=100,tz='UTC'),'total_games':20})
        masks=split_three(frame);before=residual_draws(22,[1,-2,0])
        frame.loc[masks[2],'total_games']=1000
        after=split_three(frame)
        for x,y in zip(masks[:3],after[:3]):self.assertTrue(x.equals(y))
        np.testing.assert_array_equal(before,residual_draws(22,[1,-2,0]))

if __name__=='__main__':unittest.main()

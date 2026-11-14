"""Offline chronology regressions; synthetic values, not historical forecasts."""
import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from src.sports.tennis import features as f


def fixture():
    rows = []
    for tour in ['atp', 'wta']:
        for match, day in enumerate(['2024-01-01'] * 3 + ['2024-01-22', '2024-01-23', '2024-02-15', '2024-02-15']):
            for player, opp in [(1, 2), (2, 1)]:
                row = dict(tour=tour, player_id=player, opp_id=opp,
                           tourney_id=day, match_num=match, tourney_date=pd.Timestamp(day),
                           surface='Hard', round='R32', best_of=3, player_rank=10, opp_rank=15,
                           won_match=int(player == 1), sets_won=2, bp_faced=4, svpt=40, svc_games=10)
                row.update({stat: float(match + player + (100 if tour == 'wta' else 0)) for stat in f.TARGET_STATS})
                rows.append(row)
    return pd.DataFrame(rows)


def engineered(df):
    out = f.transform_features(df)
    return out.set_index(['tour', 'player_id', 'match_num']).sort_index()


class TemporalFeaturesTest(unittest.TestCase):
    def test_mutating_same_date_and_future_does_not_change_features(self):
        raw = fixture()
        before = engineered(raw)
        changed = raw.copy()
        mask = changed.tourney_date.ge(pd.Timestamp('2024-02-15'))
        stats = f.TARGET_STATS + ['won_match', 'sets_won', 'bp_faced', 'svpt', 'svc_games']
        changed.loc[mask, stats] = 99999
        after = engineered(changed)
        cols = [c for c in before if c not in raw.columns]
        assert_frame_equal(before[cols], after[cols])

    def test_overlapping_tournament_outcomes_unavailable(self):
        raw = fixture()
        before = engineered(raw)
        changed = raw.copy()
        changed.loc[changed.tourney_date.eq(pd.Timestamp('2024-01-22')), f.TARGET_STATS + ['won_match']] = 9876
        after = engineered(changed)
        cols = [c for c in before if c not in raw.columns]
        rows = before.tourney_date.le(pd.Timestamp('2024-01-23'))
        assert_frame_equal(before.loc[rows, cols], after.loc[rows, cols])

    def test_input_order_invariance(self):
        raw = fixture()
        assert_frame_equal(engineered(raw), engineered(raw.sample(frac=1, random_state=17)))

    def test_no_cross_tour_history(self):
        raw = fixture()
        both = engineered(raw)
        atp = engineered(raw[raw.tour.eq('atp')].copy())
        assert_frame_equal(both.loc[['atp']], atp)

    def test_strict_21_day_lag(self):
        out = engineered(fixture())
        # Exactly 21 days later cannot use Jan 1 outcomes; 22 days later can.
        self.assertTrue(np.isnan(out.loc[('atp', 1, 3), 'aces_Season']))
        self.assertEqual(out.loc[('atp', 1, 3), 'career_matches'], 0)
        self.assertEqual(out.loc[('atp', 1, 4), 'career_matches'], 3)
        self.assertEqual(out.loc[('atp', 1, 4), 'aces_Season'], 2)
        self.assertEqual(out.loc[('atp', 1, 4), 'aces_hard_L10'], 2)
        self.assertEqual(out.loc[('atp', 1, 4), 'h2h_avg_games'], 2)
        self.assertTrue(np.isnan(out.loc[('atp', 1, 0), 'h2h_avg_games']))

    def test_upcoming_targets_stay_missing(self):
        raw = fixture()
        mask = raw.tourney_date.eq(pd.Timestamp('2024-02-15'))
        raw.loc[mask, f.TARGET_STATS] = np.nan
        out = f.transform_features(raw)
        self.assertEqual(len(out), len(raw))
        self.assertTrue(out.loc[out.tourney_date.eq(pd.Timestamp('2024-02-15')), f.TARGET_STATS].isna().all().all())
        self.assertTrue(out.feature_contract_version.eq(f.FEATURE_CONTRACT_VERSION).all())

    def test_whole_date_boundary_window(self):
        raw = fixture().query("tour == 'atp' and player_id == 1").copy()
        values = f._prior_mean(raw, 'aces', ['tour', 'player_id'], window=2)
        # Three Jan 1 observations are retained together, never arbitrarily cut.
        self.assertEqual(values.iloc[4], 2)


if __name__ == '__main__':
    unittest.main()

class TimezoneTest(unittest.TestCase):
    def test_utc_schedule(self):
        from src.sports.tennis.features import _prior_schedule
        rows = pd.DataFrame({'tour':['atp','atp'], 'player_id':[1,1],
            'tourney_date':pd.to_datetime(['2026-01-01','2026-03-01'],utc=True)})
        career, rest, recent = _prior_schedule(rows)
        self.assertEqual(list(career),[0,1])
        self.assertEqual(list(rest),[14,30])

import unittest
import pandas as pd
from src.sports.tennis.validation import chronological_masks

class TemporalSplitTest(unittest.TestCase):
    def test_dates_never_split_and_embargo(self):
        frame = pd.DataFrame({'tourney_date': ['2026-01-01']*3 + ['2026-02-01']*7 + ['2026-02-10']*2})
        train, test, cutoff = chronological_masks(frame, test_fraction=.34)
        self.assertEqual(str(cutoff.date()), '2026-02-01')
        self.assertEqual(train.sum(), 3)
        self.assertEqual(test.sum(), 9)
        self.assertFalse((train & test).any())
    def test_invalid_or_single_date_rejected(self):
        for dates in [['bad','2026-01-01'], ['2026-01-01']*3]:
            with self.assertRaises(ValueError):
                chronological_masks(pd.DataFrame({'tourney_date':dates}))
    def test_embargo_can_reject_insufficient_history(self):
        with self.assertRaises(ValueError):
            chronological_masks(pd.DataFrame({'tourney_date':['2026-01-01','2026-01-02']}))

import tempfile
import unittest
from pathlib import Path
import pandas as pd
from src.sports.tennis.valuebetennis import import_season_csv, symmetric_score_targets

class ValuebetennisTests(unittest.TestCase):
    def record(self, **updates):
        row=dict(match_id='7', date='2026-11-01 12:00:00', tournoi='Paris',
            tournoi_id='5', genre='atp', surface='dur intérieur', tour='10',
            joueur1='A',joueur1_id='100',joueur2='B',joueur2_id='200',
            vainqueur_id='200',score='6-4 7-6(5)')
        return dict(row, **updates)
    def load(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'matches.csv';pd.DataFrame(rows).to_csv(path,sep=';',index=False)
            return import_season_csv(path)
    def test_symmetric_targets_and_provenance(self):
        rows, report=self.load([self.record()])
        self.assertEqual(len(rows),2)
        self.assertEqual(rows.total_games.tolist(),[23,23])
        self.assertEqual(rows.total_tiebreaks.tolist(),[1,1])
        self.assertEqual(rows.player_id.tolist(),['valuebetennis:100','valuebetennis:200'])
        self.assertEqual(rows.won_match.tolist(),[0,1])
        self.assertEqual(rows.surface.tolist(),['Hard','Hard'])
        self.assertEqual(str(rows.match_time_utc.dtype),'datetime64[ns, UTC]')
        self.assertIn('creativecommons.org',rows.license_url.iloc[0])
        self.assertNotIn('games_won', rows)
        self.assertNotIn('aces', rows)
        self.assertEqual(report['accepted_matches'],1)
    def test_complete_three_and_five_set_matches(self):
        for score,games,sets in [('6-0 6-0',12,2),('6-4 4-6 6-4',30,3),
             ('6-0 6-0 6-0',18,3),('6-0 0-6 6-0 6-0',24,4),
             ('6-0 0-6 6-0 0-6 6-0',30,5)]:
            actual=symmetric_score_targets(score)
            self.assertEqual(actual['total_games'],games)
            self.assertEqual(actual['total_sets'],sets)
    def test_bad_scores_fail_closed(self):
        for score in ['6-4 2-2 ret.','w/o','6-4','6-4 3-2','6-4 4-6 [10-7]',
                      '6-4 4-6 8-6','6-4(3) 6-4','6-4 6-4 4-6','6-4 6-4 6-4 6-4']:
            with self.subTest(score=score), self.assertRaises(ValueError):
                symmetric_score_targets(score)
    def test_duplicate_identity_fails_entire_import(self):
        with self.assertRaises(ValueError):self.load([self.record(),self.record()])
    def test_missing_schema_fails(self):
        with self.assertRaises(ValueError):self.load([{'match_id':'7'}])
    def test_invalid_rows_are_counted(self):
        changes=[dict(date='bad'),dict(vainqueur_id='900'),dict(surface='moon'),
                 dict(genre='doubles'),dict(joueur2=None),dict(score='6-4 1-1 ret.')]
        rows,report=self.load([self.record(match_id=str(i),**c) for i,c in enumerate(changes)])
        self.assertTrue(rows.empty)
        self.assertEqual(report['rejected_matches'],6)
        self.assertEqual(report['accepted_matches'],0)

if __name__=='__main__':unittest.main()

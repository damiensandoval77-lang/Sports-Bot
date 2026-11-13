"""Chronological matchup training safety checks."""
import unittest
try:
    from iphone_bot.lagged_matchup_training import make_rows, COLS
except ImportError:
    from lagged_matchup_training import make_rows,COLS

class LaggedTrainingTests(unittest.TestCase):
    def test_empty_archive_is_not_fake_training(self):
        rows,excluded=make_rows([])
        self.assertEqual(rows,[])
        self.assertEqual(excluded,{})

    def test_missing_opponent_previously_not_assumed_available(self):
        rows=[]
        for n in range(13):
            rows.append({"season":"2024-25","date":f"2025-01-{n+1:02}",
                         "team":"BOS","opponent":"NYK","id":"12",
                         "game_id":f"g{n}","PTS":20.,"MIN":30.,
                         "FGA":15.,"FTA":4.,"TOV":2.,"OREB":1.,"REB":6.,"AST":4.})
        samples,excluded=make_rows(rows)
        self.assertEqual(samples,[])
        self.assertGreater(excluded.get("insufficient_opponent_history",0),0)

    def test_feature_set_does_not_claim_official_usage(self):
        self.assertNotIn("official_usage_pct",COLS)
        self.assertIn("involvement_per_min",COLS)
        self.assertIn("opponent_defense_factor",COLS)
        self.assertNotIn("postgame_injury_status",COLS)

if __name__ == "__main__":
    unittest.main()

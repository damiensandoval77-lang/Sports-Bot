import unittest
import pandas as pd
from iphone_bot.position_defense import role,positional_features,merge_training

class PositionDefenseTests(unittest.TestCase):
    def test_position_groups(self):
        self.assertEqual(role("PG"),"G")
        self.assertEqual(role("SF"),"F")
        self.assertEqual(role("C"),"C")
        self.assertIsNone(role("Unknown"))

    def sample(self):
        records=[]
        positions=[]
        for date_index in range(1,9):
            date=f"2025-01-{date_index:02d}"
            for team,opponent,base in (("GSW","MIA",10),("MIA","GSW",20)):
                for p,position in enumerate(("PG","PF","C")):
                    player=team+str(p)
                    records.append({"SEASON_ID":"2024-25","GAME_ID":str(date_index),
                      "GAME_DATE":date,"PLAYER_ID":player,
                      "TEAM_ABBREVIATION":team,"MATCHUP":team+" vs. "+opponent,
                      "PTS":base+date_index+p,"REB":5+p,"AST":3+p})
                    positions.append({"SEASON_ID":"2024-25","PLAYER_ID":player,
                                      "POSITION_ROLE":role(position)})
        return pd.DataFrame(records),pd.DataFrame(positions).drop_duplicates()

    def test_uses_previous_games_not_current(self):
        raw,positions=self.sample()
        enriched=positional_features(raw,positions)
        first=enriched[(enriched.GAME_DATE==pd.Timestamp("2025-01-01"))]
        self.assertTrue(first["DVP_PTS_L5"].isna().all())
        current=enriched[(enriched.GAME_DATE==pd.Timestamp("2025-01-05"))&
                         (enriched.PLAYER_ID=="GSW0")].iloc[0]
        # Miami allowed Golden State PG production of 11,12,13,14
        self.assertAlmostEqual(float(current["DVP_PTS_L5"]),12.5)
        # Reverse direction: Miami PG faces GSW defense, whose preceding
        # four opponent PG allowances were 21,22,23,24.
        reverse=enriched[(enriched.GAME_DATE==pd.Timestamp("2025-01-05"))&
                         (enriched.PLAYER_ID=="MIA0")].iloc[0]
        self.assertAlmostEqual(float(reverse["DVP_PTS_L5"]),22.5)

    def test_merge_does_not_expand_game_rows(self):
        raw,positions=self.sample()
        feat=positional_features(raw,positions)
        merged=merge_training(raw,feat)
        self.assertEqual(len(merged),len(raw))

if __name__=="__main__":unittest.main()

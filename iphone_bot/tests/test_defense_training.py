import unittest
import pandas as pd
from iphone_bot.defense_training import historical_defense


class DefensiveFeaturesTest(unittest.TestCase):
    def sample(self):
        data=[]
        for i in range(1,9):
            day=f"2026-01-{i:02d}"
            match=str(i)
            for team,opp,pts in (("GSW","MIA",10+i),("MIA","GSW",13+i)):
                for player in range(8):
                    data.append({"SEASON_ID":"2025-26","GAME_ID":match,
                        "GAME_DATE":day,"TEAM_ABBREVIATION":team,
                        "MATCHUP":team+" vs. "+opp,
                        "PTS":pts,"REB":4,"AST":3})
        return pd.DataFrame(data)

    def test_only_previous_opponent_games_used(self):
        features=historical_defense(self.sample())
        row=features[(features.GAME_ID=="5")&
                     (features.TEAM_ABBREVIATION=="GSW")].iloc[0]
        # GSW faces Miami: Miami previously ALLOWED GSW to score
        # 11,12,13,14 points per player in games 1-4.
        self.assertAlmostEqual(row["OPP_PTS_ALLOWED_L5"],8*(11+12+13+14)/4)
        self.assertEqual(row["OPP_DEF_SAMPLE_GAMES"],4)
        # Reverse matchup: Miami faces GSW; GSW allowed Miami's
        # 14,15,16,17 points per player. Do not confuse points
        # allowed with the defensive team's own points scored.
        reverse=features[(features.GAME_ID=="5")&
                         (features.TEAM_ABBREVIATION=="MIA")].iloc[0]
        self.assertAlmostEqual(reverse["OPP_PTS_ALLOWED_L5"],8*(14+15+16+17)/4)
        self.assertEqual(reverse["OPP_DEF_SAMPLE_GAMES"],4)

    def test_first_game_not_exposed_to_own_result(self):
        features=historical_defense(self.sample())
        first=features[features.GAME_ID=="1"]
        self.assertTrue(first["OPP_PTS_ALLOWED_L5"].isna().all())

    def test_missing_opponent_side_excludes_matchup(self):
        df=self.sample()
        df=df[~((df.GAME_ID=="3")&(df.TEAM_ABBREVIATION=="MIA"))]
        features=historical_defense(df)
        matching=features[(features.GAME_ID=="3")&(features.TEAM_ABBREVIATION=="GSW")]
        self.assertTrue(matching["OPP_PTS_ALLOWED_L5"].isna().all())


if __name__=="__main__":
    unittest.main()

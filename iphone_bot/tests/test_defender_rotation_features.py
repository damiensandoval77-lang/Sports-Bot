import unittest
import pandas as pd
from iphone_bot.defender_rotation_features import (
    prior_rotation_features,attach_rotation_to_training,FEATURE_COLS)

class DefenderRotationTests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for day in range(1,16):
            for team,opp,boost in (("GSW","MIA",0),("MIA","GSW",4)):
                for player in range(8):
                    rows.append({
                        "SEASON_ID":"2025-26",
                        "GAME_ID":str(day),
                        "GAME_DATE":f"2026-01-{day:02d}",
                        "TEAM_ABBREVIATION":team,
                        "PLAYER_ID":team+str(player),
                        "MATCHUP":team+" vs. "+opp,
                        "MIN":20+player,
                        "STL":1+boost,
                        "BLK":2,
                        "DREB":3+player})
        return pd.DataFrame(rows)

    def test_only_past_player_games_are_used(self):
        raw=self.fixture()
        features=prior_rotation_features(raw)
        first=features[(features.GAME_DATE==pd.Timestamp("2026-01-01"))&
                       (features.TEAM_ABBREVIATION=="MIA")].iloc[0]
        self.assertTrue(pd.isna(first["DR_STL_PER36"]))
        prior=features[(features.GAME_DATE==pd.Timestamp("2026-01-05"))&
                       (features.TEAM_ABBREVIATION=="MIA")].iloc[0]
        self.assertEqual(prior["DR_ROTATION_PLAYERS"],8)
        self.assertAlmostEqual(prior["DR_STL_PER36"],
                               36*5*8/sum(20+i for i in range(8)))
        amended=raw.copy()
        amended.loc[(amended.GAME_DATE=="2026-01-05")&
                    (amended.TEAM_ABBREVIATION=="MIA"),"STL"]=100
        after=prior_rotation_features(amended)
        same=after[(after.GAME_DATE==pd.Timestamp("2026-01-05"))&
                   (after.TEAM_ABBREVIATION=="MIA")].iloc[0]
        self.assertAlmostEqual(prior["DR_STL_PER36"],same["DR_STL_PER36"])

    def test_offense_receives_opponents_prior_player_stats(self):
        raw=self.fixture()
        train=raw[["SEASON_ID","GAME_DATE","TEAM_ABBREVIATION","MATCHUP","PLAYER_ID"]].copy()
        out=attach_rotation_to_training(train,raw)
        self.assertEqual(len(out),len(train))
        row=out[(out.GAME_DATE==pd.Timestamp("2026-01-05"))&
                (out.TEAM_ABBREVIATION=="GSW")].iloc[0]
        self.assertAlmostEqual(row["DR_STL_PER36"],
                               36*5*8/sum(20+i for i in range(8)))

    def test_feature_values_vary_when_opponent_changes(self):
        raw=self.fixture()
        result=prior_rotation_features(raw)
        day=result[result.GAME_DATE==pd.Timestamp("2026-01-05")]
        assert day.DR_STL_PER36.nunique()==2

if __name__=="__main__":unittest.main()

import unittest
import pandas as pd
from iphone_bot.detailed_position_defense import (
    exact_role,build_detailed_dvp,merge_detailed,DETAILED_COLS)

class DetailedPositionDefenseTest(unittest.TestCase):
    def fixture(self):
        rows=[]
        positions=[]
        for number in range(1,24):
            day=(pd.Timestamp("2025-01-01")+pd.Timedelta(days=number-1)).strftime("%Y-%m-%d")
            for team,opponent,base in (("GSW","MIA",10),("MIA","GSW",20)):
                for i,role in enumerate(("PG","SG","SF","PF","C")):
                    ident=f"{team}{i}"
                    rows.append({"SEASON_ID":"2024-25","PLAYER_ID":ident,
                        "GAME_ID":str(number),"GAME_DATE":day,
                        "TEAM_ABBREVIATION":team,"MATCHUP":team+" vs. "+opponent,
                        "PTS":base+number+i,"REB":3+i,"AST":2+i,"MIN":30})
                    positions.append({"SEASON_ID":"2024-25","PLAYER_ID":ident,
                                      "EXACT_ROLE":role})
        return pd.DataFrame(rows),pd.DataFrame(positions).drop_duplicates()

    def test_only_exact_primary_positions(self):
        self.assertEqual(exact_role("pg"),"PG")
        self.assertEqual(exact_role("SG"),"SG")
        self.assertIsNone(exact_role("G"))
        self.assertIsNone(exact_role("F"))
        self.assertIsNone(exact_role("PG/SG"))

    def test_lag_windows_and_minute_normalization(self):
        raw,lookup=self.fixture()
        feature=build_detailed_dvp(raw,lookup)
        def row(day,player):
            return feature[(feature.GAME_DATE==pd.Timestamp(day))&
                           (feature.PLAYER_ID==player)].iloc[0]
        self.assertTrue(pd.isna(row("2025-01-01","GSW0")["DVP5_PTS_AVG_L5"]))
        # Miami allowed GSW PGs 11 through 15 in games 1-5.
        r=row("2025-01-06","GSW0")
        self.assertAlmostEqual(r["DVP5_PTS_AVG_L5"],13.0)
        self.assertAlmostEqual(r["DVP5_PTS_PER36_L5"],13*36/30)
        self.assertEqual(r["DVP5_GAMES_L5"],5)
        self.assertTrue(pd.isna(r["DVP5_PTS_AVG_L10"]))
        r=row("2025-01-21","GSW0")
        self.assertAlmostEqual(r["DVP5_PTS_AVG_L5"],28.0)
        self.assertAlmostEqual(r["DVP5_PTS_AVG_L10"],25.5)
        self.assertAlmostEqual(r["DVP5_PTS_AVG_L20"],20.5)
        self.assertEqual(r["DVP5_GAMES_L20"],20)

    def test_merge_row_count(self):
        raw,lookup=self.fixture()
        enriched=build_detailed_dvp(raw,lookup)
        self.assertEqual(len(merge_detailed(raw,enriched)),len(raw))

    def test_same_game_change_does_not_change_its_own_dvp(self):
        raw,lookup=self.fixture()
        before=build_detailed_dvp(raw,lookup)
        raw.loc[(raw.PLAYER_ID=="GSW0")&
                (raw.GAME_DATE=="2025-01-15"),"PTS"]=999
        after=build_detailed_dvp(raw,lookup)
        key=lambda f:f[(f.PLAYER_ID=="GSW0")&
                        (f.GAME_DATE==pd.Timestamp("2025-01-15"))].iloc[0]
        self.assertAlmostEqual(key(before)["DVP5_PTS_AVG_L5"],key(after)["DVP5_PTS_AVG_L5"])

if __name__=="__main__":unittest.main()

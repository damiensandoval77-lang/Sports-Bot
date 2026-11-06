import unittest
from iphone_bot.matchup_context import team_allowances, defense_context, minutes_context


class MatchupContextTests(unittest.TestCase):
    def make_games(self):
        rows=[]
        for day in range(1,19):
            date=f"2026-11-{day:02d}"
            for team,opponent,pts in (("GSW","MIA",10),("MIA","GSW",12)):
                for idx in range(8):
                    rows.append({"date":date,"team":team,"opponent":opponent,
                                 "PTS":pts,"REB":3,"AST":2,"MIN":20})
        return rows

    def test_no_future_game_leakage(self):
        observed=team_allowances(self.make_games(),"2026-11-11")
        self.assertEqual(len(observed["MIA"]),10)
        self.assertEqual(len(observed["GSW"]),10)
        self.assertEqual(observed["MIA"][-1][1]["PTS"],80)
        self.assertEqual(observed["MIA"][-1][1]["PRA"],120)

    def test_descriptive_defense_only_after_sufficient_games(self):
        observed=team_allowances(self.make_games(),"2026-11-18")
        d=defense_context(observed,"MIA","PTS")
        self.assertIsNotNone(d)
        self.assertEqual(d["allowed_l5"],80)
        self.assertEqual(d["games"],5)
        self.assertEqual(d["type"],"DESCRIPTIVE_TEAM_TOTALS_NOT_POSITIONAL")

    def test_missing_reciprocal_game_rejected(self):
        games=[g for g in self.make_games() if not(g["date"]=="2026-11-05" and g["team"]=="MIA")]
        observed=team_allowances(games,"2026-11-11")
        self.assertEqual(len(observed["GSW"]),9)

    def test_minutes_warning_is_not_projected_minutes(self):
        g=[{"MIN":v} for v in (32,31,30,12,10)]
        result=minutes_context(g)
        self.assertTrue(result["review_needed"])
        self.assertIsNone(result["projected_minutes"])
        self.assertIsNone(result["confirmed_injury_status"])


if __name__ == "__main__":
    unittest.main()

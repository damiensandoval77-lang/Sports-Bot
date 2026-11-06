import unittest
from iphone_bot.projection_explanation import explain_projection

class ProjectionExplanationTest(unittest.TestCase):
    def test_summary_uses_actual_form_and_model_values(self):
        r=explain_projection("PTS",24.5,28.0,26.0,27.0,
            {"PTS_L5":29.3,"PTS_L10":25.8},
            {"observed_l5":34.2,"review_needed":False})
        self.assertEqual(r["status"],"DESCRIPTIVE_FACTS_NOT_CAUSAL_EXPLANATION")
        self.assertIn("29.3",r["sentences"][0])
        self.assertIn("25.8",r["sentences"][0])
        self.assertIn("34.2",r["sentences"][0])
        self.assertIn("27.0",r["sentences"][1])
        self.assertEqual(len(r["sentences"]),2)

    def test_absent_shadow_is_explicit_and_does_not_invent_reason(self):
        r=explain_projection("AST",4.5,5.0,None,5.0,{})
        self.assertTrue(any("unavailable" in s for s in r["sentences"]))
        self.assertFalse(r["injury_verified"])
        self.assertFalse(r["defender_assignment_verified"])

    def test_pra_uses_sum_of_lagged_stats(self):
        r=explain_projection("PRA",32.5,30.0,32.0,31.0,
           {"PTS_L5":20.0,"REB_L5":6.0,"AST_L5":5.0})
        self.assertIn("31.0",r["sentences"][0])

    def test_opponent_and_real_team_defense_are_in_reasoning(self):
        r=explain_projection("REB",5.5,6.0,6.4,6.2,
            {"REB_L5":5.8},opponent="MIA",
            defense={"vs_league_pct":-8.3,"games":5})
        self.assertEqual(len(r["sentences"]),3)
        self.assertIn("Opponent: MIA",r["sentences"][1])
        self.assertIn("8.3%",r["sentences"][1])
        self.assertIn("fewer",r["sentences"][1])
        self.assertIn("team-wide context",r["sentences"][1])

    def test_opponent_without_defensive_data_is_not_invented(self):
        r=explain_projection("AST",3.5,4.1,None,4.1,{},
            opponent="CLE",defense=None)
        self.assertIn("Opponent: CLE",r["sentences"][1])
        self.assertIn("unavailable",r["sentences"][1])

    def test_reject_unknown_market(self):
        with self.assertRaises(ValueError):
            explain_projection("STEALS",1.5,2,2,2,{})

if __name__=="__main__":unittest.main()

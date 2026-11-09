"""Expanded matchup model must fail closed on missing roles and injury labels."""
import unittest
try:
    from iphone_bot.expanded_matchup_research import expanded_predict,defense_factor,build_team_games,position_context
except ImportError:
    from expanded_matchup_research import expanded_predict,defense_factor,build_team_games,position_context


def player(day, team="BOS", opp="NYK", points=20.0):
    return {"date":day,"season":"2025-26","id":"1","team":team,
        "opponent":opp,"PTS":points,"MIN":30.0,
        "FGA":16.0,"FTA":4.0,"TOV":2.0,"OREB":1.0}


class ExpandedTests(unittest.TestCase):
    def test_no_future_opponent_context(self):
        t={"BOS":[("2026-01-09",{"poss":100.,"PTS":100},{"poss":100.,"PTS":100})]*6,
           "NYK":[("2026-01-09",{"poss":100.,"PTS":300},{"poss":100.,"PTS":100})]*6}
        r=defense_factor(t,"BOS","NYK","2026-01-09")
        self.assertEqual(r["factor"],1.0)
        self.assertEqual(r["opponent_games"],0)

    def test_missing_defense_does_not_fabricate(self):
        r=defense_factor({},"BOS","NYK","2026-01-09")
        self.assertEqual(r["status"],"NO_VERIFIED_PREGAME_DEFENSIVE_SAMPLE")
        self.assertEqual(r["factor"],1.)

    def test_no_inferred_usage_or_injury(self):
        prior=[player(f"2026-01-{d:02d}") for d in range(1,9)]
        r=expanded_predict(prior,"2026-01-09","BOS","NYK",{},player_id="1",
                           official_usage_pct=44.0,usage_source_verified=False,
                           verified_out_ids=("2",),pretip_injury_verified=False)
        self.assertEqual(r["status"],"EXPANDED_PREGAME_RESEARCH")
        self.assertIsNone(r["official_usage_pct"])
        self.assertFalse(r["verified_teammate_absence_applied"])
        self.assertFalse(r["production_modified"])
        self.assertEqual(r["opponent_adjustment_count"],0)

    def test_usage_context_is_not_blind_multiplier(self):
        prior=[player(f"2026-01-{d:02d}") for d in range(1,9)]
        a=expanded_predict(prior,"2026-01-09","BOS","NYK",{},player_id="1")
        b=expanded_predict(prior,"2026-01-09","BOS","NYK",{},player_id="1",
                           official_usage_pct=35.0,usage_source_verified=True)
        self.assertEqual(a["projection"],b["projection"])
        self.assertEqual(b["official_usage_pct"],35.0)
        self.assertFalse(b["official_usage_applied"])

    def test_position_not_called_defender_assignment(self):
        r=position_context(None,"NYK","2026-01-09","G")
        self.assertEqual(r["factor"],1.0)
        self.assertIn("UNAVAILABLE",r["status"])

    def test_reciprocal_teams_required(self):
        rows=[player("2026-01-01",team="BOS",opp="NYK") for _ in range(10)]
        self.assertEqual(dict(build_team_games(rows)),{})


if __name__=="__main__":
    unittest.main()

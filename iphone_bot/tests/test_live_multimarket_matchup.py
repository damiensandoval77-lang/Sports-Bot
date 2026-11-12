"""Multimarket forecast must sum and derive PRA on correlated components."""
import unittest
import numpy as np
try:
    from iphone_bot.multimarket_probability import simulate
    from iphone_bot.live_multimarket_matchup import select_standard,resolve_current_roster_identity,per_game_diagnostics
except ImportError:
    from multimarket_probability import simulate
    from live_multimarket_matchup import select_standard,resolve_current_roster_identity,per_game_diagnostics

class MultimarketTests(unittest.TestCase):
    def test_game_diagnostics_explain_withheld_quotes_without_inventing_picks(self):
        game="Brooklyn Nets @ New Orleans Pelicans"
        offer={"game":game,"player":"Observed Player","stat":"Points","direction":"More"}
        report=per_game_diagnostics({"picks":[offer,offer]},[offer],[],{game:{"CURRENT_ROSTER_IDENTITY_NOT_VERIFIED":1}})
        self.assertEqual(report[game]["observed_provider_quote_rows"],2)
        self.assertEqual(report[game]["verified_standard_offers"],1)
        self.assertEqual(report[game]["frozen_forecasts"],0)
        self.assertEqual(report[game]["excluded"],{"CURRENT_ROSTER_IDENTITY_NOT_VERIFIED":1})

    def test_game_diagnostics_keep_matchups_separate(self):
        a="Los Angeles Lakers @ Milwaukee Bucks"
        b="San Antonio Spurs @ Chicago Bulls"
        offers=[{"game":a},{"game":b}]
        report=per_game_diagnostics({"picks":offers},offers,[{"game":b}],{a:{"INJURY_AFFECTED_PROJECTION_WITHHELD":1}})
        self.assertEqual(report[a]["frozen_forecasts"],0)
        self.assertEqual(report[b]["frozen_forecasts"],1)
        self.assertEqual(report[b]["excluded"],{})

    def test_pra_is_same_three_component_projections(self):
        samples=np.tile([[-5,-3,-2],[0,0,0],[5,3,2],[3,1,1]],(300,1))
        p={"PTS":20.,"REB":7.,"AST":6.}
        a=simulate(p,33.5,"PRA",samples,"fixture")
        b=simulate(p,16.5,"PTS",samples,"fixture")
        self.assertEqual(a["projection"],33.)
        self.assertEqual(a["component_projections"],{"PTS":20.,"REB":7.,"AST":6.})
        self.assertTrue(a["PRA_joint_distribution"])
        self.assertFalse(b["PRA_joint_distribution"])
        self.assertNotEqual(a["modeled_more_probability"],b["modeled_more_probability"])

    def test_correlated_errors_not_independent(self):
        samples=np.tile([[10,6,4],[-10,-6,-4]],(600,1))
        a=simulate({"PTS":20.,"REB":7.,"AST":6.},50.5,"PRA",samples,"fix")
        self.assertGreater(a["modeled_more_probability"],.45)
        self.assertLess(a["modeled_more_probability"],.55)

    def test_all_four_markets_standard_only(self):
        offers=[]
        for stat in ("Points","Rebounds","Assists","Points Rebounds Assists"):
            for tier,line in (("standard",20.5),("goblin",15.5),("demon",28.5)):
                for side in ("More","Less"):
                    offers.append({"stat":stat,"pickem_tier":tier,"line":line,
                        "direction":side,"player":"Example","team":"BOS",
                        "game":"Boston Celtics @ New York Knicks",
                        "start":"2026-11-10T00:00:00Z"})
        selected,excluded=select_standard(offers)
        self.assertEqual(len(selected),4)
        self.assertEqual({r["stat"] for r in selected},
                         {"Points","Rebounds","Assists","Points Rebounds Assists"})
        self.assertTrue(all(r["line"]==20.5 for r in selected))
        self.assertEqual(excluded["NON_STANDARD_POINTS_TIER"],16)

    def test_traded_history_resolves_only_latest_verified_team_in_matchup(self):
        roster={"example":{("123","BOS"),("123","NYK")}}
        latest={"123":"NYK"}
        identity,reason=resolve_current_roster_identity(
            "Example","Boston Celtics @ New York Knicks",roster,latest)
        self.assertIsNone(reason)
        self.assertEqual(identity,("123","NYK","BOS"))

    def test_older_team_cannot_resurrect_stale_roster_identity(self):
        roster={"example":{("123","BOS"),("123","NYK")}}
        identity,reason=resolve_current_roster_identity(
            "Example","Boston Celtics @ Philadelphia 76ers",roster,{"123":"NYK"})
        self.assertIsNone(identity)
        self.assertEqual(reason,"CURRENT_ROSTER_IDENTITY_NOT_VERIFIED")

    def test_same_name_two_players_ambiguous_in_matchup_is_rejected(self):
        roster={"example":{("123","BOS"),("789","NYK")}}
        identity,reason=resolve_current_roster_identity(
            "Example","Boston Celtics @ New York Knicks",roster,
            {"123":"BOS","789":"NYK"})
        self.assertIsNone(identity)
        self.assertEqual(reason,"PLAYER_IDENTITY_NOT_UNIQUE")

    def test_invalid_fixture_fails_closed(self):
        identity,reason=resolve_current_roster_identity(
            "Example","Boston Celtics @ Boston Celtics",
            {"example":{("123","BOS")}},{"123":"BOS"})
        self.assertIsNone(identity)
        self.assertEqual(reason,"GAME_TEAM_IDENTITY_MISMATCH")

    def test_absent_validated_triplets_fails(self):
        with self.assertRaises(ValueError):
            simulate({"PTS":20,"REB":7,"AST":6},32.5,"PRA",np.zeros((3,3)),"game")

if __name__=="__main__":
    unittest.main()

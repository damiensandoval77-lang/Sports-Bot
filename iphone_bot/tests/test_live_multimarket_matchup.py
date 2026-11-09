"""Multimarket forecast must sum and derive PRA on correlated components."""
import unittest
import numpy as np
try:
    from iphone_bot.multimarket_probability import simulate
    from iphone_bot.live_multimarket_matchup import select_standard
except ImportError:
    from multimarket_probability import simulate
    from live_multimarket_matchup import select_standard

class MultimarketTests(unittest.TestCase):
    def test_pra_is_same_three_component_projections(self):
        samples=np.tile([[-5,-3,-2],[0,0,0],[5,3,2],[3,1,1]],(300,1))
        p={"PTS":20.,"REB":7.,"AST":6.}
        a=simulate(p,33.5,"PRA",samples,"fixture")
        b=simulate(p,20.5,"PTS",samples,"fixture")
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

    def test_absent_validated_triplets_fails(self):
        with self.assertRaises(ValueError):
            simulate({"PTS":20,"REB":7,"AST":6},32.5,"PRA",np.zeros((3,3)),"game")

if __name__=="__main__":
    unittest.main()

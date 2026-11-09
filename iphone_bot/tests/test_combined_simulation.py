import unittest
from iphone_bot.combined_simulation import simulate_combined_hit_rate, METHOD, DRAWS

class CombinedSimulationTests(unittest.TestCase):
    def setUp(self):
        self.errors = [float(i % 21 - 10) for i in range(2100)]

    def test_reproducible_20k_and_direction(self):
        a = simulate_combined_hit_rate(25, 22.5, self.errors, ("p1","PTS","2026-11-09",22.5))
        b = simulate_combined_hit_rate(25, 22.5, self.errors, ("p1","PTS","2026-11-09",22.5))
        self.assertEqual(a,b)
        self.assertEqual(a["simulation_count"],20000)
        self.assertEqual(a["method"],METHOD)
        self.assertEqual(a["direction"],"Over")
        self.assertEqual(a["selected_hit_rate"],a["over_hit_rate"])
        self.assertFalse(a["calibrated"])
        self.assertFalse(a["combined_residuals_validated"])
        self.assertAlmostEqual(a["over_hit_rate"] + a["under_hit_rate"] + a["push_rate"],1,places=4)

    def test_under_side_and_no_lean(self):
        under = simulate_combined_hit_rate(18,20,self.errors,"under")
        self.assertEqual(under["direction"],"Under")
        self.assertEqual(under["selected_hit_rate"],under["under_hit_rate"])
        neutral=simulate_combined_hit_rate(20,20,self.errors,"neutral")
        self.assertEqual(neutral["direction"],"Neutral")
        self.assertIsNone(neutral["selected_hit_rate"])

    def test_verified_upcoming_opponent_conditioning_changes_distribution_not_center(self):
        defense={"opponent":"BOS","league_avg":110.0,"vs_league_pct":-6.0}
        history=[96,108,91,115,101,93,120,105,94,109]
        identity=("player-1","PTS","2026-11-10",20.5)
        neutral=simulate_combined_hit_rate(22.3,20.5,self.errors,identity)
        matchup=simulate_combined_hit_rate(
            22.3,20.5,self.errors,identity,opponent="BOS",
            defense_history=history,opponent_defense=defense)
        self.assertEqual(matchup["simulation_count"],20000)
        self.assertEqual(matchup["opponent_conditioning"]["status"],
                         "APPLIED_OPPONENT_HISTORICAL_GAME_SCENARIOS")
        self.assertEqual(matchup["opponent_conditioning"]["opponent"],"BOS")
        self.assertEqual(matchup["opponent_conditioning"]["opponent_vs_league_pct"],-6.0)
        self.assertFalse(matchup["opponent_conditioning"]["mean_shift_applied"])
        self.assertNotEqual(matchup["over_hit_rate"],neutral["over_hit_rate"])
        self.assertEqual(matchup,simulate_combined_hit_rate(
            22.3,20.5,self.errors,identity,opponent="BOS",
            defense_history=history,opponent_defense=defense))
        self.assertFalse(matchup["calibrated"])

    def test_no_future_or_mismatched_opponent_context_falls_back_without_fake_defense(self):
        report={"opponent":"BOS","league_avg":110.0,"vs_league_pct":-6.0}
        unconditioned=simulate_combined_hit_rate(22,21,self.errors,"same")
        wrong=simulate_combined_hit_rate(22,21,self.errors,"same",
                opponent="NYK",defense_history=[95]*10,opponent_defense=report)
        missing=simulate_combined_hit_rate(22,21,self.errors,"same",
                opponent="BOS",defense_history=[95,96],opponent_defense=report)
        self.assertEqual(unconditioned["over_hit_rate"],wrong["over_hit_rate"])
        self.assertEqual(unconditioned["over_hit_rate"],missing["over_hit_rate"])
        self.assertEqual(wrong["opponent_conditioning"]["status"],
                         "UNAVAILABLE_INSUFFICIENT_PRIOR_DEFENSE")
        self.assertNotIn("position_dvp_available",wrong["opponent_conditioning"])

    def test_no_automatic_duplicate_mean_adjustment_against_strong_defense(self):
        # Fixed allowed defensive production means no additional variation,
        # even when the team concedes materially fewer stats than league avg.
        strong={"opponent":"BOS","league_avg":115.0,"vs_league_pct":-20.0}
        base=simulate_combined_hit_rate(19.4,19.5,self.errors,"fixed")
        conditioned=simulate_combined_hit_rate(
            19.4,19.5,self.errors,"fixed",opponent="BOS",
            defense_history=[92]*10,opponent_defense=strong)
        self.assertEqual(conditioned["over_hit_rate"],base["over_hit_rate"])
        self.assertFalse(conditioned["opponent_conditioning"]["mean_shift_applied"])

    def test_reject_short_history_and_wrong_draws(self):
        with self.assertRaises(ValueError):
            simulate_combined_hit_rate(20,19,[1,2,3],"short")
        with self.assertRaises(ValueError):
            simulate_combined_hit_rate(20,19,self.errors,"wrong",draws=10000)

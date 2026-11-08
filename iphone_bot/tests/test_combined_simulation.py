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

    def test_reject_short_history_and_wrong_draws(self):
        with self.assertRaises(ValueError):
            simulate_combined_hit_rate(20,19,[1,2,3],"short")
        with self.assertRaises(ValueError):
            simulate_combined_hit_rate(20,19,self.errors,"wrong",draws=10000)

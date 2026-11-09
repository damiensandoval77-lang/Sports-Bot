"""Per-offer over/under estimates vary with line and reject fake confidence."""
import unittest
import numpy as np
try:
    from iphone_bot.points_hit_probability import make_reference,estimate,DRAWS
except ImportError:
    from points_hit_probability import make_reference,estimate,DRAWS

class HitChanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        projections=np.tile(np.array([5.,13.,24.,35.]),450)
        # Nonzero, deterministic residuals in all scoring buckets.
        actual=np.maximum(0,projections+np.tile(np.array([-6.,-2.,2.,6.]),450))
        cls.reference=make_reference(projections,actual)

    def test_probabilities_change_with_actual_line(self):
        a=estimate(24,19.5,self.reference,("p","2026-11-10",19.5))
        b=estimate(24,28.5,self.reference,("p","2026-11-10",28.5))
        self.assertEqual(a["draws"],20000)
        self.assertGreater(a["estimated_over_probability"],b["estimated_over_probability"])
        self.assertGreater(a["estimated_over_probability"],.5)
        self.assertLess(b["estimated_over_probability"],.5)
        self.assertFalse(a["calibrated"])
        self.assertFalse(a["betting_edge_verified"])

    def test_deterministic_same_event_identity(self):
        a=estimate(13,13.5,self.reference,"sample")
        b=estimate(13,13.5,self.reference,"sample")
        self.assertEqual(a,b)

    def test_over_under_push_sum_one(self):
        r=estimate(13,13,self.reference,"integer-line")
        self.assertAlmostEqual(
            r["estimated_over_probability"]+
            r["estimated_under_probability"]+
            r["estimated_push_probability"],1.0,places=3)

    def test_no_unverified_reference(self):
        with self.assertRaises(ValueError):estimate(20,21.5,{},"sample")

    def test_not_enough_residuals(self):
        with self.assertRaises(ValueError):make_reference([10.]*200,[12.]*200)

    def test_reject_nonstandard_draw_count(self):
        with self.assertRaises(ValueError):
            estimate(20,21.5,self.reference,"sample",draws=10000)

if __name__=="__main__":
    unittest.main()

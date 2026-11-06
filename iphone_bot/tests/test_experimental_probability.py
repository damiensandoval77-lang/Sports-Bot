import unittest
from iphone_bot.experimental_probability import probability_sides,METHOD

class ExperimentalProbabilityTests(unittest.TestCase):
    def setUp(self):
        self.residuals=[float(x)/10 for x in range(-1500,1500)]

    def test_over_and_under_reverse_order_with_line(self):
        high=probability_sides(25,20,self.residuals)
        low=probability_sides(15,20,self.residuals)
        self.assertGreater(high["over"],low["over"])
        self.assertLess(high["under"],low["under"])
        self.assertEqual(high["method"],METHOD)

    def test_empirical_probs_are_bounded_and_no_guarantees(self):
        for estimate in (probability_sides(10,10000,self.residuals),
                         probability_sides(10000,10,self.residuals)):
            self.assertTrue(0<estimate["over"]<1)
            self.assertTrue(0<estimate["under"]<1)
            self.assertAlmostEqual(sum(estimate[s] for s in ("over","under","push")),1.0)

    def test_reject_insufficient_calibration(self):
        with self.assertRaises(ValueError):
            probability_sides(10,11,[-1,0,1])

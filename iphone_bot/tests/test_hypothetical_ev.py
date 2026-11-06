import unittest
import numpy as np
from iphone_bot.hypothetical_ev import (
    american_profit_per_unit,implied_probability,no_vig_probabilities,
    hypothetical_ev,approximate_discrete_probabilities,hypothetical_quote_analysis)

class HypotheticalEvTests(unittest.TestCase):
    def test_american_prices_and_breakeven(self):
        self.assertAlmostEqual(american_profit_per_unit(110),1.1)
        self.assertAlmostEqual(american_profit_per_unit(-110),100/110)
        self.assertAlmostEqual(implied_probability(-110),110/210)
        with self.assertRaises(ValueError):american_profit_per_unit(-50)

    def test_no_vig_sums_one(self):
        fair=no_vig_probabilities(-110,-110)
        self.assertAlmostEqual(fair["over"],0.5)
        self.assertAlmostEqual(fair["under"],0.5)

    def test_positive_and_negative_theoretical_ev(self):
        self.assertAlmostEqual(hypothetical_ev(110,.6,.4),.26)
        self.assertAlmostEqual(hypothetical_ev(-110,.4,.6),.4*100/110-.6)
        self.assertAlmostEqual(hypothetical_ev(100,.6,.3,.1),.3)
        with self.assertRaises(ValueError):hypothetical_ev(100,.9,.9)

    def test_discrete_push_when_line_is_integer(self):
        residuals=np.tile([-1.0,0.0,1.0,2.0],500)
        p=approximate_discrete_probabilities(20.0,20.0,residuals)
        self.assertGreater(p["push"],0.2)
        self.assertAlmostEqual(sum(p.values()),1.0)
        half=approximate_discrete_probabilities(20.0,20.5,residuals)
        self.assertLess(half["push"],0.001)

    def test_own_line_for_each_book(self):
        errors=np.tile([-1.0,0.0,1.0,2.0],500)
        a=hypothetical_quote_analysis({"name":"A","line":20.5,"over":110,"under":-120},20,errors)
        b=hypothetical_quote_analysis({"name":"B","line":21.5,"over":110,"under":-120},20,errors)
        self.assertGreater(a["hypothetical_over_ev_pct"],b["hypothetical_over_ev_pct"])
        self.assertFalse(a["ev_verified"])
        self.assertEqual(a["ev_method"],"UNCALIBRATED_MODEL_HYPOTHETICAL_EV")

if __name__=="__main__":unittest.main()

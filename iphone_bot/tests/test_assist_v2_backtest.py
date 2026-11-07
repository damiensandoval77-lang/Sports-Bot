import unittest
from iphone_bot.assist_v2_backtest import compare

class PairedAssistV2Tests(unittest.TestCase):
    def test_no_markets_does_not_promote(self):
        result=compare([],[])
        self.assertEqual(result["baseline"]["observations"],0)
        self.assertTrue(result["live_model_unchanged"])
        self.assertEqual(result["promotion_gate"]["status"],"BLOCKED_PENDING_PROSPECTIVE_VALIDATION")

if __name__=="__main__":
    unittest.main()

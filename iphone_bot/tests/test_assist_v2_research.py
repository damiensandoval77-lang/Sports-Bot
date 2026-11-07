import unittest
from iphone_bot.assist_v2_research import forecast

class AssistV2Tests(unittest.TestCase):
    def setUp(self):
        self.logs = [{"date": f"2026-10-{i:02d}", "team": "AAA",
                      "MIN": 30, "AST": 5} for i in range(1, 13)]

    def test_does_not_use_future_or_other_team(self):
        logs = self.logs + [{"date": "2026-11-07", "team": "AAA", "MIN": 30, "AST": 50},
                            {"date": "2026-10-12", "team": "BBB", "MIN": 30, "AST": 50}]
        result = forecast(logs, "2026-11-06", "AAA", 30, line=4.5, simulations=100)
        self.assertEqual(result["prior_games"], 12)
        self.assertLess(result["projection"], 10)
        self.assertFalse(result["live_applied"])

    def test_repeatable_simulation(self):
        a = forecast(self.logs, "2026-11-06", "AAA", 30, line=4.5, simulations=1000)
        b = forecast(self.logs, "2026-11-06", "AAA", 30, line=4.5, simulations=1000)
        self.assertEqual(a, b)

    def test_missing_data_not_fabricated(self):
        a = forecast(self.logs[:4], "2026-11-06", "AAA", 30)
        self.assertEqual(a["status"], "INSUFFICIENT_PREGAME_DATA")

if __name__ == "__main__":
    unittest.main()

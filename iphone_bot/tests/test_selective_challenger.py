import unittest
from iphone_bot.selective_challenger import screen,evaluate,RULE

class SelectiveChallengerTests(unittest.TestCase):
    def test_agreement_and_margin(self):
        x=screen("PTS",20.5,25,24.5,24.75)
        self.assertEqual(x["decision"],"CONSIDER")
        self.assertEqual(x["side"],"OVER")
        self.assertEqual(screen("PTS",20.5,25,18,22)["reason"],"MODELS_DISAGREE")
        self.assertEqual(screen("PTS",20.5,22,22,22)["reason"],"INSUFFICIENT_PROJECTION_MARGIN")
        self.assertEqual(screen("AST",4.5,6.5,None,6.0)["decision"],"PASS")
        self.assertEqual(screen("PTS",20.5,25,25,20.5)["decision"],"PASS")

    def test_only_earlier_locked_choices_and_deduplicated_outcomes(self):
        before={"status":"SETTLED","player_id":"9","event_start":"2026-11-09T00:00:00Z",
                "captured_at":"2026-11-08T23:00:00Z","team":"BOS",
                "market":"PTS","bookmaker":"A","line":20.5,"actual":24,
                "over_odds":-110,"under_odds":-110,
                "research_selective_v1":screen("PTS",20.5,25,25,25)}
        duplicate={**before,"bookmaker":"B"}
        legacy={**before,"player_id":"OLD","research_selective_v1":None}
        report=evaluate([before,duplicate,legacy])
        self.assertEqual(report["locked_markets"],1)
        self.assertEqual(report["considered_markets"],1)
        self.assertEqual(report["by_stat"]["PTS"]["wins"],1)
        self.assertEqual(report["by_stat"]["PTS"]["hit_rate"],1.)
        self.assertEqual(report["by_stat"]["AST"]["n"],0)
        self.assertTrue(report["historical_unscreened_excluded"])

    def test_no_records_avoids_fake_win_rate(self):
        report=evaluate([])
        self.assertEqual(report["rule"],RULE)
        self.assertIsNone(report["by_stat"]["PTS"]["hit_rate"])
        self.assertEqual(report["considered_markets"],0)

if __name__=="__main__":unittest.main()

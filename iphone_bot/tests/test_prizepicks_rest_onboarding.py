import unittest
from iphone_bot.prizepicks_rest_onboarding import first_join

class PrizePicksRESTJoinTests(unittest.TestCase):
    def test_flat_training_rows_join_prior_games_without_target_leakage(self):
        training=[{"projection_id":"sample","player":"Test Athlete","team":"BOS",
                   "stat":"Rebounds","game_date":"2026-10-28",
                   "closing_line":8.5,"actual_value":11,"result":"over",
                   "closing_observed_at":"2026-10-28T22:00:00Z"}]
        logs=[{"player":"Test Athlete","team":"BOS","stats_player_id":"sp_111",
               "game_date":"2026-10-25","points":18,"assists":4,"rebounds":7},
              {"player":"Test Athlete","team":"BOS","stats_player_id":"sp_111",
               "game_date":"2026-10-27","points":22,"assists":5,"rebounds":9},
              {"player":"Test Athlete","team":"BOS","stats_player_id":"sp_111",
               "game_date":"2026-10-28","points":55,"assists":20,"rebounds":35},
              {"player":"Test Athlete","team":"NYK","stats_player_id":"sp_other",
               "game_date":"2026-10-26","points":99,"assists":99,"rebounds":99}]
        match=first_join(training,logs)
        self.assertEqual(match["prior_games"],2)
        self.assertEqual(match["prior_rebounds_mean"],8.0)
        self.assertEqual(match["last_prior_game"],"2026-10-27")
        self.assertEqual(match["join_method"],"EXACT_PLAYER_NAME_AND_TEAM")
        self.assertEqual(match["actual_value_label_only"],11)
        self.assertTrue(match["leakage_safe"])
    def test_no_pretip_history_returns_no_match(self):
        self.assertIsNone(first_join([{"player":"A","team":"BOS",
                    "game_date":"2026-10-28"}],
                    [{"player":"A","team":"BOS","game_date":"2026-10-28",
                      "points":10}]))

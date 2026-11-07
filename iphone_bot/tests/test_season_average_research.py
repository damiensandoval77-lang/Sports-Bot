import unittest
from iphone_bot.season_average_research import season_candidate,report,METHOD

class SeasonAverageResearchTests(unittest.TestCase):
    def games(self):
        return [{"date":f"2026-11-{day:02d}","team":"BOS","PTS":float(day),
                 "REB":2.0,"AST":3.0,"PRA":float(day+5)}
                for day in range(1,9)]
    def test_strict_prior_mean_and_future_leakage(self):
        past=self.games()
        a=season_candidate(past,"2026-11-09","BOS","PTS",20)
        self.assertEqual(a["season_games"],8)
        self.assertEqual(a["season_average"],4.5)
        self.assertAlmostEqual(a["research_projection"],16.9)
        future=past+[{"date":"2026-11-09","team":"BOS","PTS":1000},
                     {"date":"2026-11-08","team":"MIA","PTS":800}]
        self.assertEqual(season_candidate(future,"2026-11-09","BOS","PTS",20),a)
        self.assertFalse(a["production_applied"])
    def test_missing_samples_not_fake_average(self):
        result=season_candidate(self.games()[:4],"2026-11-09","BOS","PTS",20)
        self.assertEqual(result["status"],"INSUFFICIENT_PREGAME_SEASON_GAMES")
        self.assertIsNone(result["research_projection"])
    def test_only_prospective_locked_records_graded(self):
        info=season_candidate(self.games(),"2026-11-09","BOS","PTS",20)
        row={"status":"SETTLED","captured_at":"2026-11-09T00:00:00Z",
             "event_start":"2026-11-09T20:00:00Z","player_id":"99",
             "team":"BOS","market":"PTS","actual":18.0,"line":17.5,
             "combined_projection":20,"season_average_challenger":info}
        results=report([row,{**row,"bookmaker":"another"},
                        {**row,"player_id":"old","season_average_challenger":None}])
        self.assertEqual(results["method"],METHOD)
        self.assertEqual(results["locked_markets"],1)
        self.assertEqual(results["settled"],1)
        self.assertAlmostEqual(results["challenger_mae"],1.1)
        self.assertEqual(results["baseline_direction_wins"],1)
        self.assertEqual(results["challenger_direction_wins"],0)
    def test_no_backfill(self):
        self.assertEqual(report([{"status":"SETTLED"}])["settled"],0)
        self.assertIsNone(report([])["challenger_mae"])
if __name__=="__main__":unittest.main()

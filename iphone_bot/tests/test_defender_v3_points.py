"""Points research uses independently verified player points, historical minutes and defense only."""
import unittest
import pyarrow as pa
from iphone_bot.defender_v3_points import (
    load_player_games,load_defender_games,defender_adjustment,evaluate)


class DefenderPointsTests(unittest.TestCase):
    def test_defender_proxy_capped_and_weighted_by_recent_minutes(self):
        baseline={"expected_points":25.,"expected_2pa":12.,"expected_3pa":8.}
        hard={"two_a":100.,"two_m":18.,"three_a":70.,"three_m":15.}
        neutral={"two_a":100.,"two_m":52.,"three_a":70.,"three_m":25.}
        pred,delta=defender_adjustment(baseline,[(30,hard),(10,neutral),(2,neutral)])
        self.assertIsNotNone(delta)
        self.assertLess(pred,25)
        self.assertGreaterEqual(delta,-2)
        self.assertEqual(defender_adjustment(baseline,[(30,hard)])[1],None)

    def test_actual_points_is_independent_and_validated(self):
        table=pa.Table.from_pylist([
          {"player_id":10,"game_id":"0022500001","game_date":"2025-10-25",
           "team":"BOS","opponent":"NYK","minutes":30.,"pts":20,
           "fgm":7,"fga":15,"fg3m":2,"fg3a":6,"ftm":4,"fta":5},
          {"player_id":11,"game_id":"0022500001","game_date":"2025-10-25",
           "team":"NYK","opponent":"BOS","minutes":32.,"pts":24,
           "fgm":9,"fga":19,"fg3m":3,"fg3a":8,"ftm":3,"fta":4}])
        boxes=load_player_games(table)
        self.assertEqual(len(boxes),2)
        self.assertEqual(boxes[0]["PTS"],20.)
        matchup=pa.Table.from_pylist([{
          "game_id":"0022500001","person_id":11,
          "matchups_person_id":10,"team_tricode":"NYK",
          "matchup_minutes":"11:00","partial_possessions":20.,
          "matchup_field_goals_attempted":8.,
          "matchup_field_goals_made":3.,
          "matchup_three_pointers_attempted":3.,
          "matchup_three_pointers_made":1.,
          "_season":2025,"_season_type":"rg"}])
        tracked,rejected=load_defender_games(matchup,boxes)
        self.assertEqual(len(tracked),1)
        self.assertEqual(tracked[0]["off_id"],"10")
        self.assertEqual(tracked[0]["def_id"],"11")
        self.assertEqual(tracked[0]["two_a"],5.)
        self.assertEqual(tracked[0]["three_m"],1.)

    def test_wrong_defender_team_is_rejected(self):
        sample=[{"player_id":10,"game_id":"0022500001","game_date":"2025-10-25",
           "team":"BOS","opponent":"NYK","minutes":30.,"pts":20,
           "fgm":7,"fga":15,"fg3m":2,"fg3a":6,"ftm":4,"fta":5},
          {"player_id":11,"game_id":"0022500001","game_date":"2025-10-25",
           "team":"NYK","opponent":"BOS","minutes":32.,"pts":24,
           "fgm":9,"fga":19,"fg3m":3,"fg3a":8,"ftm":3,"fta":4}]
        boxes=load_player_games(pa.Table.from_pylist(sample))
        wrong=pa.Table.from_pylist([{"game_id":"0022500001","person_id":11,
          "matchups_person_id":10,"team_tricode":"BOS",
          "matchup_minutes":"11:00","partial_possessions":20.,
          "matchup_field_goals_attempted":8.,
          "matchup_field_goals_made":3.,
          "matchup_three_pointers_attempted":3.,
          "matchup_three_pointers_made":1.,
          "_season":2025,"_season_type":"rg"}])
        tracked,rejected=load_defender_games(wrong,boxes)
        self.assertFalse(tracked)
        self.assertEqual(rejected.get("team_or_day_mismatch"),1)

    def test_insufficient_samples_fail_closed(self):
        self.assertEqual(evaluate([{"date":"2025-10-25"}],[])["status"],
                         "INSUFFICIENT_SAME_GAME_POINTS_SAMPLE")


if __name__=="__main__":unittest.main()

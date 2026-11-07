"""Points research uses independently verified player points, historical minutes and defense only."""
import unittest
import pyarrow as pa
from iphone_bot.defender_v3_points import (
    load_player_games,load_defender_games,defender_adjustment,head_to_head_adjustment,date_cluster_interval,evaluate)


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

    def test_head_to_head_exposure_requires_prior_defender_pair(self):
        base={"expected_points":25.,"expected_2pa":12.,"expected_3pa":8.,
              "expected_2p_pct":.52,"expected_3p_pct":.36}
        defender={"two_a":80,"two_m":20,"three_a":40,"three_m":10}
        rotated=[("21",30,defender),("22",30,defender),("23",15,defender)]
        blank=head_to_head_adjustment(base,rotated,{},"10")
        self.assertEqual(blank,(25.,None,0))
        history={("10","21"):{"poss":60,"two_a":40,"two_m":10,
                               "three_a":20,"three_m":5}}
        estimate,shift,coverage=head_to_head_adjustment(base,rotated,history,"10")
        self.assertEqual(coverage,1)
        self.assertLess(estimate,25)
        self.assertGreaterEqual(shift,-2)
        other=head_to_head_adjustment(base,rotated,history,"999")
        self.assertIsNone(other[1])

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

    def test_date_cluster_interval_reports_uncertainty_not_false_certainty(self):
        self.assertIsNone(date_cluster_interval({"2026-01-01":[-1.0,10]}))
        observations={f"2026-01-{i:02d}":[(-1 if i%2 else 1),1]
                      for i in range(1,21)}
        bounds=date_cluster_interval(observations)
        self.assertEqual(len(bounds),2)
        self.assertLess(bounds[0],0)
        self.assertGreater(bounds[1],0)

    def test_insufficient_samples_fail_closed(self):
        self.assertEqual(evaluate([{"date":"2025-10-25"}],[])["status"],
                         "INSUFFICIENT_SAME_GAME_POINTS_SAMPLE")


if __name__=="__main__":unittest.main()

import unittest
from iphone_bot.stress_test_20k_research import check,DRAWS,SCENARIOS

CAPTURE="2026-11-07T18:00:00Z"
START="2026-11-08T01:00:00Z"

def history():
    values=[14,18,23,20,27,25,17,26,22,19,24,21]
    return [{"id":"101","team":"DEN","date":f"2026-10-{day:02d}",
             "PTS":pts,"REB":4+day%5,"AST":2+day%4,"PRA":pts+6+day%5+day%4,
             "MIN":30.} for day,pts in enumerate(values,start=19)]

def audit(history_rows=None,**kwargs):
    args={"team":"DEN","market":"PTS","projection":23.,"line":20.5,
          "captured_at":CAPTURE,"event_start":START,"expected_minutes":30.,
          "injury_status":"AVAILABLE","injury_source":"OFFICIAL_NBA_REPORT",
          "player_id":"101"}
    args.update(kwargs)
    return check(history() if history_rows is None else history_rows,**args)

class StressTest20KResearchTests(unittest.TestCase):
    def test_six_scenarios_20000_each_and_deterministic(self):
        one=audit()
        two=audit()
        self.assertEqual(one,two)
        self.assertEqual(one["simulation_draws_per_scenario"],20000)
        self.assertEqual(len(one["simulated_scenarios"]),6)
        self.assertEqual(set(one["simulated_scenarios"]),
                         {x[0] for x in SCENARIOS})
        self.assertEqual(one["status"],"CONDITIONAL_STRESS_RESEARCH_ONLY")
        self.assertFalse(one["probabilities_calibrated"])
        self.assertFalse(one["live_probability_modified"])
        self.assertFalse(one["production_picks_modified"])

    def test_over_reacts_to_lower_minutes_and_variance(self):
        r=audit()
        scenarios=r["simulated_scenarios"]
        self.assertLessEqual(scenarios["MINUTES_MINUS_3"]["conditional_hit_probability"],
                             scenarios["MINUTES_PLUS_3"]["conditional_hit_probability"])
        self.assertEqual(r["worst_case_conditional_hit_probability"],
                         min(x["conditional_hit_probability"] for x in scenarios.values()))

    def test_under_reacts_to_more_minutes(self):
        r=audit(projection=18.,line=23.5)
        self.assertEqual(r["projected_side"],"UNDER")
        scenarios=r["simulated_scenarios"]
        self.assertGreaterEqual(scenarios["MINUTES_MINUS_3"]["conditional_hit_probability"],
                                scenarios["MINUTES_PLUS_3"]["conditional_hit_probability"])

    def test_injury_unverified_remains_hypothetical(self):
        r=audit(injury_status="QUESTIONABLE",injury_source="ESPN")
        self.assertIn("UNVERIFIED_INJURY_OR_LINEUP",r["warnings"])
        self.assertFalse(r["probabilities_calibrated"])

    def test_no_post_tip_and_future_games(self):
        future=history()+[{"id":"101","team":"DEN","date":"2026-11-07",
                           "PTS":200,"REB":20,"AST":20,"MIN":30}]
        self.assertEqual(audit(history_rows=future)["simulated_scenarios"],
                         audit()["simulated_scenarios"])
        self.assertEqual(audit(captured_at="2026-11-08T02:00:00Z")["status"],
                         "LATE_CAPTURE_REJECTED")

    def test_current_season_and_missing_minutes_fail_closed(self):
        old=[{**r,"date":r["date"].replace("2026","2025")} for r in history()]
        self.assertEqual(audit(history_rows=old)["status"],
                         "INSUFFICIENT_PREGAME_HISTORY")
        self.assertEqual(audit(expected_minutes=None)["status"],
                         "INVALID_OR_MISSING_INPUTS")

    def test_constant_historical_rates_do_not_create_fake_certainty(self):
        h=[{**r,"PTS":20.} for r in history()]
        self.assertEqual(audit(history_rows=h)["status"],
                         "INSUFFICIENT_HISTORICAL_VARIABILITY")
        self.assertIsNone(audit(history_rows=h)["raw_baseline_conditional_hit_probability"])

    def test_duplicate_conflicts_are_not_arbitrarily_selected(self):
        h=history()
        conflict={**h[0],"PTS":99}
        r=audit(history_rows=h+[conflict,h[0]])
        self.assertEqual(r["history_games"],11)

    def test_no_direction_and_invalid_inputs(self):
        self.assertEqual(audit(projection=20.5,line=20.5)["status"],"NO_PROJECTED_SIDE")
        self.assertEqual(audit(projection=float("nan"))["status"],"INVALID_OR_MISSING_INPUTS")
        self.assertEqual(audit(market="TOV")["status"],"UNSUPPORTED_MARKET")

    def test_high_confidence_fragility_threshold_is_observable(self):
        # Fixed research threshold; no claim that .9 is verified.
        r=audit(projection=35.,line=24.)
        if r["raw_baseline_conditional_hit_probability"]>=.9:
            self.assertEqual(r["fragile_high_confidence"],
                (r["worst_case_conditional_hit_probability"]<.75 or
                 r["confidence_drop_percentage_points"]>=15))
        self.assertTrue(all(0<=v["conditional_hit_probability"]<=1
            for v in r["simulated_scenarios"].values()))

if __name__=="__main__":
    unittest.main()

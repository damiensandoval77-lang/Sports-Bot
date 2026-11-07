"""Pregame snapshot integrity, injury dates, opponent V4 gate and 10k auditing."""
import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.projection_upgrade_research import (
    snapshot,official_injuries,research_simulations,grade_shadow,grade_injury_scenarios,grade_opportunity_shadows,run)

NOW="2026-11-06T23:00:00Z"
START="2026-11-07T01:00:00Z"  # Nov 6 Eastern
def board():
    return {"status":"EXPERIMENTAL_NON_CALIBRATED",
        "verified_current_matchups":True,"generated_at":"2026-11-06T22:55:00Z",
        "comparisons":[{"player":"Target Player","player_id":"10",
          "team":"BOS","stat":"PTS","start":START,"game":"Boston Celtics @ New York Knicks",
          "line":20.5,"projection":21.,"combined_projection":22.,
          "minutes_research":{"expected_minutes":30.,"observed_l5":28.},
          "shot_profile_research":{"expected_fga":16.},
          "injury_minutes_research":{"status":"HISTORICAL_SCENARIO_RESEARCH_ONLY",
             "teammate_id":"99","scenario_minutes":32.},
          "teammate_absence_splits":[{"teammate":"Real Teammate",
            "with_games":8,"without_games":5,"with_avg":20.,"without_avg":24.}]}]}
def injury(issue="2026-11-06T22:30:00Z",day="2026-11-06",verified=True):
    return {"status":"OFFICIAL_NBA_REPORT_VERIFIED" if verified else "THIRD_PARTY_ESPN_INJURY_CONTEXT",
       "injury_data_verified":verified,"report_issued_at":issue,
       "generated_at":"2026-11-06T22:40:00Z",
       "players":[{"player":"Teammate","player_id":"99","team":"BOS",
                   "game_date":day,"status":"Out"}]}

class ResearchTests(unittest.TestCase):
    def test_pregame_frozen_snapshot_and_no_live_modification(self):
        existing=[]
        original=board()
        rows,stats=snapshot(original,injury(),existing,NOW)
        self.assertEqual(stats["new"],1)
        r=rows[0]
        self.assertEqual(r["injury_scenario"]["status"],"PREGAME_CONDITIONAL_NOT_CAUSAL")
        self.assertEqual(r["injury_scenario"]["scenario_minutes"],32.)
        self.assertAlmostEqual(r["injury_scenario"]["scenario_points_projection"],
                               22*(32/30),places=2)
        self.assertTrue(r["injury_scenario"]["research_only"])
        self.assertEqual(r["opportunity"]["expected_fga_unverified"],16.)
        self.assertEqual(len(r["teammate_on_off_observed"]),1)
        self.assertIsNone(r["v4_shadow_projection"])
        self.assertFalse(r["simulated_probability_modified"])
        self.assertEqual(original["comparisons"][0]["combined_projection"],22.)
        rerun,counters=snapshot(original,injury(),rows,NOW)
        self.assertEqual(rerun,rows)
        self.assertEqual(counters.get("new",0),0)

    def test_no_future_or_wrong_date_injury_claim(self):
        for source in (injury(issue="2026-11-07T02:00:00Z"),
                       injury(day="2026-11-07"),injury(verified=False)):
            rows,_=snapshot(board(),source,[],NOW)
            self.assertEqual(rows[0]["injury_scenario"]["status"],
                             "NO_VERIFIED_PREGAME_MINUTES_SCENARIO")
            self.assertEqual(rows[0]["verified_out_teammate_ids"],[])

    def test_no_post_tipoff_snapshot(self):
        with self.assertRaises(ValueError):
            snapshot(board(),injury(),[],"2026-11-07T02:30:00Z")
        b=board()
        b["generated_at"]="2026-11-07T02:00:00Z"
        with self.assertRaises(ValueError):
            snapshot(b,injury(),[],NOW)

    def test_no_simulations_without_settled_prior_residuals(self):
        info=research_simulations([])
        for stat in ("PTS","REB","AST","PRA"):
            self.assertEqual(info[stat]["simulation_count"],10000)
            self.assertIsNone(info[stat]["brier_score"])
            self.assertEqual(info[stat]["evaluated_later_markets"],0)

    def test_10k_calibration_requires_prior_settled_markets(self):
        # One thousand earlier actuals train a residual distribution; all
        # later games must be scored without observing their same-day result.
        observations=[]
        for i in range(1040):
            day="2026-10-01T19:00:00Z" if i<1000 else "2026-10-02T19:00:00Z"
            observations.append({"status":"SETTLED","event_start":day,
                "captured_at":"2026-09-30T18:00:00Z",
                "player_id":str(i),"market":"PTS",
                "original_projection":22.,"line":20.5,"actual":22.})
        result=research_simulations(observations)
        self.assertEqual(result["PTS"]["evaluated_later_markets"],40)
        self.assertEqual(result["PTS"]["simulation_count"],10000)
        self.assertEqual(result["PTS"]["brier_score"],0.0)
        self.assertEqual(result["REB"]["evaluated_later_markets"],0)

    def test_injury_candidate_only_graded_against_matching_locked_actual(self):
        pregame,_=snapshot(board(),injury(),[],NOW)
        actual=[{"status":"SETTLED","event_start":START,
                 "captured_at":NOW,"player_id":"10","market":"PTS",
                 "original_projection":21.,"line":20.5,"actual":24.}]
        grade=grade_injury_scenarios(pregame,actual)
        self.assertEqual(grade["overall"]["paired_observations"],1)
        self.assertLess(grade["overall"]["injury_candidate_mae"],
                        grade["overall"]["baseline_mae"])
        self.assertTrue(grade["no_live_adjustment"])

    def test_pregame_opportunity_shadow_uses_only_prior_team_games(self):
        past=[{"id":"10","team":"BOS",
            "date":f"2026-10-{day:02d}","MIN":30.,
            "PTS":20.,"REB":6.,"AST":5.,"FGA":14.}
            for day in range(20,30)]
        a,_=snapshot(board(),injury(),[],NOW,past)
        self.assertIsNotNone(a[0]["opportunity_shadow_projection"])
        self.assertEqual(a[0]["opportunity_shadow_status"],
                         "PREGAME_LOCKED_UNVALIDATED_CHALLENGER")
        self.assertLess(a[0]["opportunity_shadow_last_game"],"2026-11-06")
        future=[{"id":"10","team":"BOS","date":"2026-11-06",
                 "MIN":45.,"PTS":100.,"REB":40.,"AST":20.,"FGA":50.}]
        b,_=snapshot(board(),injury(),[],NOW,past+future)
        self.assertEqual(a[0]["opportunity_shadow_projection"],
                         b[0]["opportunity_shadow_projection"])
        self.assertFalse(b[0]["simulated_probability_modified"])
        self.assertEqual(b[0]["combined_projection"],22.)

    def test_shadow_results_require_saved_pretip_candidate(self):
        past=[{"id":"10","team":"BOS",
            "date":f"2026-10-{day:02d}","MIN":30.,
            "PTS":20.,"REB":6.,"AST":5.,"FGA":14.}
            for day in range(20,30)]
        locked,_=snapshot(board(),injury(),[],NOW,past)
        outcomes=[{"status":"SETTLED","event_start":START,
                 "captured_at":NOW,"player_id":"10","market":"PTS",
                 "original_projection":21.,"line":20.5,"actual":24.}]
        with_shadow=grade_opportunity_shadows(locked,outcomes)
        self.assertEqual(with_shadow["overall"]["paired_markets"],1)
        without_shadow=grade_opportunity_shadows(
             [{**locked[0],"opportunity_shadow_projection":None}],outcomes)
        self.assertEqual(without_shadow["overall"]["paired_markets"],0)
        self.assertFalse(with_shadow["eligible_for_live_promotion"])

    def test_shadow_only_scores_actual_immutable_capture(self):
        rows,_=snapshot(board(),injury(),[],NOW)
        self.assertEqual(grade_shadow(rows,[])["paired_markets"],0)
        self.assertFalse(grade_shadow(rows,[])["v4_live_applied"])
        info=run(board(),injury(),[],[],NOW)[1]
        self.assertTrue(info["live_combined_ai_unchanged"])
        self.assertEqual(info["promotion_gate"],
                         "NO_LIVE_ADJUSTMENT_WITHOUT_PRE_GAME_VALIDATION")

if __name__=="__main__":unittest.main()

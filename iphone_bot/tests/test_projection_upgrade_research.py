"""Pregame snapshot integrity, injury dates, opponent V4 gate and 20k auditing."""
import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.projection_upgrade_research import (
    snapshot,official_injuries,research_simulations,grade_shadow,grade_injury_scenarios,grade_opportunity_shadows,grade_opponent_v2,grade_rebound_v1,grade_tracking_opportunities,grade_licensed_onoff_shadows,grade_sanity_shadow,stress_research_report,run)

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
    def test_rebound_shadow_is_locked_and_graded_only_at_exact_pretip_line(self):
        b=board()
        b["comparisons"][0].update(stat="REB",line=6.5,projection=5.8,
                                   combined_projection=6.0)
        past=[{"id":"10","team":"BOS","date":f"2026-10-{d:02d}",
               "MIN":30.,"PTS":14.,"REB":8.,"AST":3.,"FGA":10.}
              for d in range(15,25)]
        locked,counts=snapshot(b,injury(),[],NOW,past)
        result=locked[0]["rebound_shadow_v1"]
        self.assertEqual(result["status"],"PRETIP_REBOUND_OPPORTUNITY_SHADOW")
        self.assertAlmostEqual(result["projection"],6.6)
        self.assertEqual(counts["rebound_shadow_v1_locked"],1)
        self.assertEqual(b["comparisons"][0]["combined_projection"],6.0)
        final={"status":"SETTLED","event_start":START,"captured_at":NOW,
            "player_id":"10","market":"REB","original_projection":5.8,
            "line":6.5,"actual":8.}
        score=grade_rebound_v1(locked,[final])
        self.assertEqual(score["paired_markets"],1)
        self.assertEqual(score["same_frozen_line_eligible"],1)
        self.assertEqual(score["baseline_wins"],0)
        self.assertEqual(score["shadow_wins"],1)
        self.assertFalse(score["validated_for_live"])
        mismatched=grade_rebound_v1(locked,[{**final,"line":7.5}])
        self.assertEqual(mismatched["same_frozen_line_eligible"],0)
        self.assertEqual(grade_rebound_v1(locked,[])["paired_markets"],0)
        after=snapshot(b,injury(),locked,NOW,past)[0]
        self.assertEqual(after,locked)

    def test_authorized_chances_are_frozen_and_scored_on_same_line_only(self):
        from iphone_bot.tests.test_tracking_opportunities_v1 import feed
        b=board()
        hist=[{"id":"10","team":"BOS","date":f"2026-10-{d:02d}",
               "MIN":30.,"PTS":14.,"REB":8.,"AST":6.,"FGA":10.}
              for d in range(15,25)]
        source=feed()
        source["generated_at"]="2026-11-06T22:45:00Z"
        # Both assists and rebounds use the same authorized observed games.
        cards=[]
        for market,baseline,line in (("AST",4.,4.5),("REB",6.,6.25)):
            b2=board()
            b2["comparisons"][0].update(stat=market,line=line,
               combined_projection=baseline,projection=baseline)
            rows,info=snapshot(b2,injury(),[],NOW,hist,None,source)
            shadow=rows[0]["tracking_opportunity_shadow"]
            self.assertEqual(shadow["status"],"PREGAME_TRACKING_OPPORTUNITY_SHADOW")
            self.assertFalse(shadow["live_applied"])
            self.assertEqual(info["tracking_opportunity_shadow_locked"],1)
            self.assertEqual(b2["comparisons"][0]["combined_projection"],baseline)
            cards.append(rows[0])
        final=[]
        for r in cards:
            final.append({"status":"SETTLED","event_start":START,
               "captured_at":NOW,"player_id":"10","market":r["market"],
               "original_projection":r["combined_projection"],
               "line":r["line"],"actual":8.})
        graded=grade_tracking_opportunities(cards,final)
        self.assertEqual(graded["overall"]["paired_markets"],2)
        self.assertEqual(graded["overall"]["exact_line_eligible"],2)
        self.assertFalse(graded["eligible_for_production"])
        wrong=[{**p,"line":p["line"]+1} for p in final]
        self.assertEqual(grade_tracking_opportunities(cards,wrong)["overall"]["exact_line_eligible"],0)
        self.assertEqual(snapshot(b2,injury(),[cards[-1]],NOW,hist,None,source)[0],[cards[-1]])
        denied=dict(source)
        denied["licensed_use_verified"]=False
        rows,_=snapshot(b2,injury(),[],NOW,hist,None,denied)
        self.assertIsNone(rows[0]["tracking_opportunity_shadow"]["projection"])

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

    def test_sanity_shadow_locks_only_verified_pregame_and_grades_pair(self):
        past=[{"id":"10","team":"BOS","date":f"2026-10-{day:02d}",
               "MIN":30.,"PTS":40.,"REB":6.,"AST":5.,"FGA":20.}
              for day in range(20,30)]
        b=board()
        b["comparisons"][0]["minutes_research"]["expected_minutes"]=30.
        b["comparisons"][0]["injury_status"]="AVAILABLE"
        b["comparisons"][0]["injury_status_source"]="OFFICIAL_NBA_REPORT"
        official=injury()
        official["players"].append({"player":"Target Player","player_id":"10",
                                   "team":"BOS","game_date":"2026-11-06",
                                   "status":"Available"})
        locked,_=snapshot(b,official,[],NOW,past)
        sanity=locked[0]["sanity_shadow_v1"]
        self.assertEqual(sanity["status"],"SHADOW_CANDIDATE_UNVALIDATED")
        self.assertGreater(sanity["shadow_projection"],22.)
        self.assertFalse(sanity["live_applied"])
        self.assertEqual(b["comparisons"][0]["combined_projection"],22.)
        actual=[{"status":"SETTLED","event_start":START,
                 "captured_at":NOW,"player_id":"10","market":"PTS",
                 "original_projection":21.,"line":20.5,"actual":40.}]
        grade=grade_sanity_shadow(locked,actual)
        self.assertEqual(grade["overall"]["paired_markets"],1)
        self.assertFalse(grade["accuracy_gain_established"])
        nofeed,_=snapshot(b,injury(verified=False),[],NOW,past)
        self.assertEqual(nofeed[0]["sanity_shadow_v1"]["status"],
                         "REVIEW_ONLY_UNCERTAIN_INPUTS")
        self.assertEqual(grade_sanity_shadow(nofeed,actual)["overall"]["paired_markets"],0)

    def test_sanity_shadow_coverage_separates_adjustments_from_copies(self):
        def rec(pid,kind,candidate,base=25,event=START):
            return {"status":"PENDING","player_id":str(pid),"team":"BOS",
                    "market":"PTS","event_start":event,"captured_at":NOW,
                    "combined_projection":base,"sanity_shadow_v1":{
                      "status":kind,"shadow_projection":candidate}}
        originals=[
            rec("1","SHADOW_CANDIDATE_UNVALIDATED",27),
            rec("2","NO_LARGE_DEVIATION",25),
            rec("3","REVIEW_ONLY_UNCERTAIN_INPUTS",None),
            rec("4","SHADOW_CANDIDATE_UNVALIDATED",26),
            rec("5","SHADOW_CANDIDATE_UNVALIDATED",28)
        ]
        finals=[{"status":"SETTLED","event_start":START,
                 "captured_at":NOW,"player_id":pid,"market":"PTS",
                 "original_projection":25.,"line":23.5,"actual":actual}
                for pid,actual in (("1",28.),("2",23.),("3",24.),("4",29.))]
        result=grade_sanity_shadow(originals,finals)
        self.assertEqual(result["captured_independent_markets"],5)
        self.assertEqual(result["overall"]["paired_markets"],3)
        self.assertEqual(result["adjusted_only"]["paired_markets"],2)
        self.assertEqual(result["pending_by_status"]["SHADOW_CANDIDATE_UNVALIDATED"],1)
        self.assertEqual(result["excluded_uncertain_by_status"]["REVIEW_ONLY_UNCERTAIN_INPUTS"],1)
        self.assertEqual(result["overall"]["distinct_game_dates"],1)
        self.assertFalse(result["accuracy_gain_established"])
        again=grade_sanity_shadow(originals+[dict(originals[0])],finals)
        self.assertEqual(again["adjusted_only"],result["adjusted_only"])

    def test_missing_legacy_sanity_field_not_rebuilt_after_tipoff(self):
        row={"status":"PENDING","player_id":"1","team":"BOS",
             "market":"PTS","event_start":START,"captured_at":NOW,
             "combined_projection":25}
        outcomes=[{"status":"SETTLED","event_start":START,
                   "captured_at":NOW,"player_id":"1","market":"PTS",
                   "original_projection":25,"line":21.5,"actual":30}]
        result=grade_sanity_shadow([row],outcomes)
        self.assertEqual(result["captured_independent_markets"],0)
        self.assertEqual(result["overall"]["paired_markets"],0)

    def test_conditional_stress_is_frozen_pretip_and_not_live(self):
        games=[{"id":"10","team":"BOS","date":f"2026-10-{d:02d}",
                "PTS":18+(d%7),"REB":5+(d%3),"AST":4+(d%2),
                "MIN":30.,"FGA":14.} for d in range(18,30)]
        b=board()
        pre,_=snapshot(b,injury(),[],NOW,games)
        saved=pre[0]["stress_test_20k_v1"]
        self.assertEqual(saved["status"],"CONDITIONAL_STRESS_RESEARCH_ONLY")
        self.assertEqual(saved["simulation_draws_per_scenario"],20000)
        self.assertEqual(len(saved["simulated_scenarios"]),6)
        self.assertFalse(saved["probabilities_calibrated"])
        self.assertFalse(saved["live_projection_modified"])
        self.assertEqual(b["comparisons"][0]["combined_projection"],22.)
        scored=[{"status":"SETTLED","event_start":START,"captured_at":NOW,
                 "player_id":"10","market":"PTS","original_projection":21.,
                 "line":20.5,"actual":25.}]
        report=stress_research_report(pre,scored)
        self.assertEqual(report["independent_stress_tested_markets"],1)
        self.assertEqual(report["paired_settled_stress_markets"],1)
        self.assertFalse(report["performance_improvement_established"])
        self.assertEqual(stress_research_report(pre+pre,scored)["paired_settled_stress_markets"],1)

    def test_old_research_rows_without_stress_do_not_get_backfilled(self):
        row={"captured_at":NOW,"event_start":START,"player_id":"10","market":"PTS"}
        result=stress_research_report([row],[])
        self.assertEqual(result["independent_stress_tested_markets"],0)
        self.assertFalse(result["calibrated_probability"])

    def test_model_disagreement_frozen_without_mutating_board(self):
        b=board()
        b["comparisons"][0]["shadow_projection"]=18.
        b["comparisons"][0]["shadow_status"]="RESEARCH_SHADOW_ONLY"
        frozen,_=snapshot(b,injury(),[],NOW)
        result=frozen[0]["model_disagreement_v1"]
        self.assertEqual(result["independent_models_available"],2)
        self.assertEqual(result["status"],"MODEL_DISAGREEMENT_REVIEW")
        self.assertIn("ORIGINAL_OPPONENT_DIRECTION_CONFLICT",result["flags"])
        self.assertEqual(b["comparisons"][0]["combined_projection"],22.)
        self.assertFalse(result["pick_changed"])
        self.assertFalse(result["probability_changed"])
        repeat,_=snapshot(b,injury(),frozen,NOW)
        self.assertEqual(repeat,frozen)

    def test_missing_opponent_is_not_claimed_as_agreement(self):
        frozen,_=snapshot(board(),injury(),[],NOW)
        result=frozen[0]["model_disagreement_v1"]
        self.assertEqual(result["status"],"PARTIAL_MODEL_COVERAGE")
        self.assertIn("OPPONENT_MODEL_UNAVAILABLE",result["flags"])

    def test_unified_reliability_preserves_pregame_research_warnings(self):
        history=[{"id":"10","team":"BOS","date":f"2026-10-{d:02d}",
                  "MIN":30.,"PTS":18+d%7,"REB":5.,"AST":4.,"FGA":14.}
                 for d in range(18,30)]
        b=board()
        b["comparisons"][0]["shadow_projection"]=18.
        b["comparisons"][0]["shadow_status"]="RESEARCH_SHADOW_ONLY"
        ledger,status=run(b,injury(),[],[],NOW,history)
        combined=status["unified_reliability_v1"]
        self.assertEqual(combined["independent_research_markets"],1)
        self.assertEqual(combined["classification_counts"]["NEEDS_REVIEW"],1)
        self.assertIn("MODELS_ORIGINAL_OPPONENT_DIRECTION_CONFLICT",
                      combined["recent_markets"][0]["reasons"])
        self.assertTrue(combined["no_live_picks_changed"])
        self.assertTrue(combined["no_accuracy_improvement_claimed"])
        self.assertEqual(b["comparisons"][0]["combined_projection"],22.)

    def test_no_simulations_without_settled_prior_residuals(self):
        info=research_simulations([])
        for stat in ("PTS","REB","AST","PRA"):
            self.assertEqual(info[stat]["simulation_count"],20000)
            self.assertIsNone(info[stat]["brier_score"])
            self.assertEqual(info[stat]["evaluated_later_markets"],0)

    def test_20k_calibration_requires_prior_settled_markets(self):
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
        self.assertEqual(result["PTS"]["simulation_count"],20000)
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

    def test_stability_opportunity_shadow_is_frozen_pretip_and_scored(self):
        prior=[{"id":"10","team":"BOS","date":f"2026-10-{d:02d}",
                "MIN":28.+(d%3),"PTS":19.,"REB":6.,"AST":5.,"FGA":14.}
               for d in range(19,30)]
        frozen,_=snapshot(board(),injury(),[],NOW,prior)
        r=frozen[0]
        self.assertIsNotNone(r["stability_opportunity_shadow_projection"])
        self.assertEqual(r["stability_opportunity_method"],
                         "FIXED_VOLATILITY_SHRINKAGE_RESEARCH_ONLY")
        self.assertFalse(r["simulated_probability_modified"])
        self.assertEqual(r["combined_projection"],22.)
        finished=[{"status":"SETTLED","event_start":START,
                   "captured_at":NOW,"player_id":"10","market":"PTS",
                   "original_projection":21.,"line":20.5,"actual":24.}]
        report=grade_opportunity_shadows(frozen,finished)
        self.assertEqual(report["overall"]["stability_shadow_paired_markets"],1)
        self.assertEqual(report["overall"]["stability_shadow_same_line_eligible"],1)
        self.assertFalse(report["eligible_for_live_promotion"])
        no_candidate=grade_opportunity_shadows(
            [{**r,"stability_opportunity_shadow_projection":None}],finished)
        self.assertEqual(no_candidate["overall"]["stability_shadow_paired_markets"],0)

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

    def test_all_market_shadow_paired_direction_requires_exact_pregame_line(self):
        locked=[]
        settled=[]
        for i,market in enumerate(("PTS","REB","AST","PRA")):
            player=str(i+1)
            locked.append({
                "event_start":START,"captured_at":NOW,
                "player_id":player,"market":market,
                "combined_projection":7.0,"opportunity_shadow_projection":9.0,
                "line":8.5})
            settled.append({"status":"SETTLED","event_start":START,
                "captured_at":NOW,"player_id":player,"market":market,
                "original_projection":7.0,
                "line":8.5 if market!="REB" else 9.5,"actual":10.0})
        report=grade_opportunity_shadows(locked,settled)
        self.assertEqual(report["overall"]["paired_markets"],4)
        self.assertEqual(report["overall"]["same_line_direction_eligible"],3)
        self.assertEqual(report["overall"]["baseline_correct_directions"],0)
        self.assertEqual(report["overall"]["opportunity_correct_directions"],3)
        self.assertEqual(report["overall"]["line_mismatched_final_markets"],1)
        self.assertEqual(report["capture_coverage"]["settled_quote_line_mismatch"],1)
        self.assertEqual(report["by_market"]["REB"]["paired_markets"],1)
        self.assertEqual(report["by_market"]["REB"]["same_line_direction_eligible"],0)
        self.assertIsNone(report["by_market"]["REB"]["opportunity_same_line_hit_rate"])
        self.assertEqual(report["overall"]["distinct_game_dates"],1)
        self.assertFalse(report["eligible_for_live_promotion"])

    def test_all_market_shadow_reports_pending_without_claiming_hits(self):
        rows=[{"event_start":START,"captured_at":NOW,"player_id":str(i),
               "market":market,"line":5.5,"combined_projection":5.0,
               "opportunity_shadow_projection":6.0}
              for i,market in enumerate(("PTS","REB","AST","PRA"))]
        r=grade_opportunity_shadows(rows,[])
        self.assertEqual(r["overall"]["paired_markets"],0)
        self.assertEqual(r["overall"]["same_line_direction_eligible"],0)
        self.assertEqual(r["capture_coverage"]["captured_candidate_markets"],4)
        self.assertEqual(set(r["pending_by_market"].values()),{1})
        self.assertTrue(r["same_line_required_for_direction_scoring"])

    def test_opponent_v2_freezes_all_market_context_and_scores_exact_lines(self):
        logs=[]
        for d in range(1,19):
            day=f"2026-10-{d:02d}"
            for team,other,pts in (("BOS","NYK",14),("NYK","BOS",12)):
                for i in range(8):
                    logs.append({"id":str(i)+"-"+team,"date":day,"team":team,
                        "opponent":other,"PTS":pts,"REB":5,"AST":3,"MIN":27,
                        "FGA":10,"FTA":3,"OREB":2,"TOV":2})
        b=board()
        b["comparisons"]=[]
        for i,m in enumerate(("PTS","REB","AST","PRA")):
            example=board()["comparisons"][0]
            example.update(player_id=str(i+1),stat=m)
            b["comparisons"].append(example)
        original=b["comparisons"][0]["combined_projection"]
        pre,counts=snapshot(b,injury(),[],NOW,logs)
        self.assertEqual(counts["opponent_v2_shadow_locked"],4)
        self.assertEqual(len(pre),4)
        self.assertEqual(b["comparisons"][0]["combined_projection"],original)
        for x in pre:
            self.assertEqual(x["opponent_v2_context"]["status"],
                "PACE_EFFICIENCY_PAST_ONLY")
            self.assertFalse(x["opponent_v2_context"]["individual_defender_impact_applied"])
        finals=[]
        for x in pre:
            finals.append({"status":"SETTLED","event_start":START,
                "captured_at":NOW,"player_id":x["player_id"],
                "market":x["market"],"original_projection":21.,
                "line":20.5 if x["market"]!="REB" else 21.5,"actual":23.})
        report=grade_opponent_v2(pre,finals)
        self.assertEqual(report["overall"]["paired_markets"],4)
        self.assertEqual(report["overall"]["exact_line_direction_eligible"],3)
        self.assertEqual(report["by_market"]["REB"]["exact_line_direction_eligible"],0)
        self.assertFalse(report["eligible_for_production"])
        self.assertEqual(grade_opponent_v2(pre,[])["overall"]["paired_markets"],0)

    def test_verified_out_licensed_onoff_freezes_and_grades_without_production_change(self):
        licensed={"status":"LICENSED_ON_OFF_VERIFIED","licensed_use_verified":True,
          "generated_at":"2026-11-06T22:45:00Z","source":"TEST_RIGHTS_CLEARED",
          "authorization":{"reviewed_for_betting_analytics":True,
            "allowed_use":"NBA_PROP_RESEARCH","reviewer_confirmation":"MANUALLY_VERIFIED",
            "permission_reference":"TEST_ONLY_NONPRODUCTION_FIXTURE"},
          "observations":[{"player_id":"10","teammate_id":"99","team":"BOS",
            "season":"2026-27","data_through":"2026-11-05",
            "observed_through_at":"2026-11-06T22:40:00Z",
            "with":{"games":6,"minutes":180,"PTS_per36":20},
            "without":{"games":6,"minutes":190,"PTS_per36":26}}]}
        b=board()
        original=b["comparisons"][0]["combined_projection"]
        frozen,info=run(b,injury(),[],[],NOW,[],licensed)
        self.assertEqual(info["features_covered"]["licensed_onoff_shadow_locked"],1)
        self.assertAlmostEqual(frozen[0]["licensed_onoff_shadow"]["projection"],23.25)
        self.assertFalse(frozen[0]["licensed_onoff_shadow"]["production_applied"])
        self.assertEqual(b["comparisons"][0]["combined_projection"],original)
        final=[{"status":"SETTLED","event_start":START,"captured_at":NOW,
           "player_id":"10","market":"PTS","original_projection":21,
           "line":20.5,"actual":27}]
        score=grade_licensed_onoff_shadows(frozen,final)
        self.assertEqual(score["overall"]["paired_markets"],1)
        self.assertEqual(score["overall"]["exact_line_eligible"],1)
        self.assertFalse(score["eligible_for_production"])
        wrong=grade_licensed_onoff_shadows(frozen,[{**final[0],"line":19.5}])
        self.assertEqual(wrong["overall"]["exact_line_eligible"],0)
        no_license={**licensed,"licensed_use_verified":False}
        missing,_=snapshot(b,injury(),[],NOW,[],no_license)
        self.assertIsNone(missing[0]["licensed_onoff_shadow"]["projection"])

    def test_shadow_only_scores_actual_immutable_capture(self):
        rows,_=snapshot(board(),injury(),[],NOW)
        self.assertEqual(grade_shadow(rows,[])["paired_markets"],0)
        self.assertFalse(grade_shadow(rows,[])["v4_live_applied"])
        info=run(board(),injury(),[],[],NOW)[1]
        self.assertTrue(info["live_combined_ai_unchanged"])
        self.assertEqual(info["promotion_gate"],
                         "NO_LIVE_ADJUSTMENT_WITHOUT_PRE_GAME_VALIDATION")

if __name__=="__main__":unittest.main()

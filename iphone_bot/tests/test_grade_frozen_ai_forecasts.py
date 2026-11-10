import datetime as dt
import inspect
import unittest

from iphone_bot.grade_frozen_ai_forecasts import (
    eligible_predictions,final_requests,settle_predictions,report,unresolved_reasons
)

NOW=dt.datetime(2026,11,9,15,tzinfo=dt.timezone.utc)
def forecast(player="Ace Bailey",stat="PTS"):
    return {"player_id":"1642846","player":player,"team":"UTA",
            "game":"Utah Jazz @ Minnesota Timberwolves",
            "start":"2026-11-09T00:00:00+00:00",
            "stat":stat,"projection":14.7,"line":None,"direction":None,
            "is_pregame_prediction":True,
            "captured_at":"2026-11-08T23:40:00+00:00"}
def final(player="Ace Bailey"):
    return {"player":player,"team":"UTA","opponent":"MIN",
            "date":"2026-11-08","source":"NBA_CDN_FINAL",
            "source_game_id":"0022600198","final_confirmed":True,
            "PTS":19,"REB":5,"AST":3,"PRA":27,"MIN":27.5}
class FrozenAiGradingTests(unittest.TestCase):
    def test_forecast_graded_against_verified_actual(self):
        source=forecast()
        selected=eligible_predictions([source],NOW)
        self.assertEqual(len(final_requests(selected)),1)
        result=settle_predictions(selected,[final()])
        self.assertEqual(result["new_grades"],1)
        row=result["records"][0]
        self.assertEqual(row["actual"],19)
        self.assertEqual(row["absolute_error"],4.3)
        self.assertEqual(row["error"],-4.3)
        self.assertIsNone(row["betting_grade"])
        self.assertEqual(row["projection"],14.7)
        self.assertEqual(row["captured_at"],source["captured_at"])

    def test_missing_or_unconfirmed_player_never_inferred(self):
        p=eligible_predictions([forecast()],NOW)
        for found in [[],[{**final(),"final_confirmed":False}],
                      [{**final(),"dnp_final_verified":True}],
                      [{**final(),"player":"Other Player"}],
                      [{**final(),"opponent":"UTA"}],
                      [{**final(),"date":"2026-11-07"}]]:
            self.assertEqual(settle_predictions(p,found)["new_grades"],0)

    def test_duplicate_official_identity_is_rejected(self):
        chosen=eligible_predictions([forecast()],NOW)
        self.assertEqual(settle_predictions(chosen,[final(),{**final(),"source_game_id":"0022600099"}])["new_grades"],0)

    def test_cannot_modify_or_duplicate_prior_grade(self):
        chosen=eligible_predictions([forecast()],NOW)
        first=settle_predictions(chosen,[final()])
        second=settle_predictions(chosen,[{**final(),"PTS":25}],first["records"])
        self.assertEqual(second["new_grades"],0)
        self.assertEqual(second["records"][0]["actual"],19)

    def test_verified_final_can_grade_immediately_after_tip_without_four_hour_delay(self):
        p=forecast()
        five_minutes_after_tip=dt.datetime(2026,11,9,0,5,tzinfo=dt.timezone.utc)
        chosen=eligible_predictions([p],five_minutes_after_tip)
        self.assertEqual(len(chosen),1)
        # No verified final: still explicitly pending, never a guessed result.
        self.assertEqual(settle_predictions(chosen,[])["new_grades"],0)
        self.assertEqual(settle_predictions(chosen,[final()])["new_grades"],1)

    def test_same_day_status_keeps_pending_distinct_from_verified_final(self):
        p=forecast()
        selected=eligible_predictions([p],dt.datetime(2026,11,9,0,5,tzinfo=dt.timezone.utc))
        empty=report("2026-11-08",selected,settle_predictions(selected,[]),
                     now=dt.datetime(2026,11,9,0,5,tzinfo=dt.timezone.utc),final_rows=[])
        completed=report("2026-11-08",selected,settle_predictions(selected,[final()]),
                         now=dt.datetime(2026,11,9,0,5,tzinfo=dt.timezone.utc),final_rows=[final()])
        self.assertEqual(empty["ungraded"],1)
        self.assertEqual(completed["graded"],1)
        self.assertEqual(completed["ungraded"],0)

    def test_late_capture_is_not_graded(self):
        row={**forecast(),"captured_at":"2026-11-09T00:05:00Z"}
        self.assertEqual(eligible_predictions([row],NOW),[])

    def test_unique_locked_model_and_stats_not_alternate_thresholds(self):
        pairs=[forecast(stat="PTS"),forecast(stat="REB")]
        selected=eligible_predictions(pairs,NOW)
        result=settle_predictions(selected,[final()])
        self.assertEqual(result["new_grades"],2)
        audit=report("2026-11-08",selected,result,now=NOW)
        self.assertEqual(audit["recorded_pregame_forecasts"],2)
        self.assertEqual(audit["graded"],2)
        self.assertEqual(audit["ungraded"],0)
        self.assertFalse(audit["is_betting_hit_rate"])

    def test_verified_official_inactive_excluded_without_zero_actual(self):
        chosen=eligible_predictions([forecast(player="Lauri Markkanen")],NOW)
        official={**final(player="Other Player")}
        inactive={"player":"Lauri Markkanen","team":"UTA","opponent":"MIN",
                  "date":"2026-11-08","source":"NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
                  "source_game_id":"0022600198","dnp_final_verified":True,
                  "dnp_reason":"INACTIVE_RIGHT_WRIST","final_confirmed":True}
        graded=settle_predictions(chosen,[official],confirmed_inactives=[inactive])
        self.assertEqual(graded["new_grades"],0)
        self.assertEqual(graded["new_exclusions"],1)
        row=graded["records"][0]
        self.assertEqual(row["status"],"EXCLUDED_VERIFIED_DNP")
        self.assertIsNone(row["actual"])
        self.assertIsNone(row["absolute_error"])
        self.assertIsNone(row["betting_grade"])
        audit=report("2026-11-08",chosen,graded,now=NOW)
        self.assertEqual(audit["verified_dnp_exclusions"],1)
        self.assertEqual(audit["graded"],0)
        self.assertEqual(audit["ungraded"],0)
        self.assertEqual(audit["accounted_for"],1)

    def test_cache_rebuild_keeps_explicit_boxscore_dnp_source(self):
        # Regression: the first inactivity pass included verified DNPs, but
        # the second pass after final-cache reconciliation dropped them.
        from iphone_bot import grade_frozen_ai_forecasts as grader
        source=inspect.getsource(grader.main)
        second=source.split("actuals=saved",1)[1]
        self.assertIn("verified_boxscore_dnp_subset(actuals)",second)
        self.assertIn("confirmed_inactives=confirmed_inactives",second)

    def test_missing_name_unverified_dnp_is_not_excluded(self):
        chosen=eligible_predictions([forecast(player="Other Player")],NOW)
        row={"player":"Other Player","team":"UTA","opponent":"MIN",
             "date":"2026-11-08","source":"NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
             "source_game_id":"0022600198","dnp_final_verified":False,
             "dnp_reason":"CLAIM","final_confirmed":True}
        result=settle_predictions(chosen,[],confirmed_inactives=[row])
        self.assertEqual(result["records"],[])
        self.assertEqual(result["new_exclusions"],0)

    def test_confirmed_played_and_inactive_conflict_not_silently_excluded(self):
        chosen=eligible_predictions([forecast()],NOW)
        row={"player":"Ace Bailey","team":"UTA","opponent":"MIN",
             "date":"2026-11-08","source":"NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
             "source_game_id":"0022600198","dnp_final_verified":True,
             "dnp_reason":"CLAIM","final_confirmed":True}
        result=settle_predictions(chosen,[final()],confirmed_inactives=[row])
        self.assertEqual(result["records"],[])

    def test_missing_final_matchup_is_explicit_not_a_player_loss(self):
        pending=eligible_predictions([forecast()],NOW)
        details=unresolved_reasons(pending,[])
        self.assertEqual(next(iter(details.values()))["reason"],
                         "VERIFIED_FINAL_MATCHUP_NOT_RETRIEVED")
        status=report("2026-11-08",pending,settle_predictions(pending,[]),
                      now=NOW,final_rows=[])
        self.assertEqual(status["ungraded"],1)
        self.assertEqual(status["ungraded_diagnostics"]["by_reason"],
                         {"VERIFIED_FINAL_MATCHUP_NOT_RETRIEVED":1})

    def test_final_game_present_but_player_missing_is_not_fabricated_dnp(self):
        pending=eligible_predictions([forecast()],NOW)
        rows=[final(player="Other Player")]
        details=unresolved_reasons(pending,rows)
        self.assertEqual(next(iter(details.values()))["reason"],
                         "PLAYER_NOT_IN_RETRIEVED_FINAL_ROWS_DNP_UNVERIFIED")
        self.assertEqual(settle_predictions(pending,rows)["records"],[])

    def test_wrong_team_identity_diagnosed_without_settlement(self):
        pending=eligible_predictions([forecast()],NOW)
        rows=[{**final(), "team":"MIN","opponent":"UTA"}]
        self.assertEqual(next(iter(unresolved_reasons(pending,rows).values()))["reason"],
                         "PLAYER_TEAM_OPPONENT_IDENTITY_MISMATCH")
        self.assertEqual(settle_predictions(pending,rows)["records"],[])

    def test_ungraded_count_not_falsely_success(self):
        chosen=eligible_predictions([forecast()],NOW)
        result=settle_predictions(chosen,[])
        audit=report("2026-11-08",chosen,result,now=NOW)
        self.assertEqual(audit["ungraded"],1)
        self.assertEqual(audit["ungraded_distinct_player_names_by_game"],{"Utah Jazz @ Minnesota Timberwolves":["Ace Bailey"]})
        self.assertEqual(audit["status"],"NO_VERIFIED_AI_FORECAST_ACTUALS")

if __name__=="__main__":
    unittest.main()

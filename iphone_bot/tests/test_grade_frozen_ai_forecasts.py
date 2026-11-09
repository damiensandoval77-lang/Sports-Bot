import datetime as dt
import unittest

from iphone_bot.grade_frozen_ai_forecasts import (
    eligible_predictions,final_requests,settle_predictions,report
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

    def test_ungraded_count_not_falsely_success(self):
        chosen=eligible_predictions([forecast()],NOW)
        result=settle_predictions(chosen,[])
        audit=report("2026-11-08",chosen,result,now=NOW)
        self.assertEqual(audit["ungraded"],1)
        self.assertEqual(audit["status"],"NO_VERIFIED_AI_FORECAST_ACTUALS")

if __name__=="__main__":
    unittest.main()

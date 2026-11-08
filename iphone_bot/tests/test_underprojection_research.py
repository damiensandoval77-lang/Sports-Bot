import unittest
from iphone_bot.underprojection_research import report

START="2026-11-07T00:10:00Z"
CAPTURE="2026-11-06T20:00:00Z"

def row(pid="1",actual=35,forecast=30,stat="PTS",date=START):
    return {"status":"SETTLED","event_start":date,"captured_at":CAPTURE,
      "player_id":pid,"player":"Example "+pid,"team":"BOS",
      "game":"Boston Celtics @ Charlotte Hornets","market":stat,
      "line":28.5,"actual":actual,"bookmaker":"FanDuel",
      "original_projection":forecast+2,"opponent_shadow_projection":forecast-2,
      "combined_projection":forecast,
      "season_average_challenger":{"status":"RESEARCH_CANDIDATE_NOT_VALIDATED",
          "season_average":40.,"research_projection":32.}}
class UnderprojectionTests(unittest.TestCase):
    def test_signed_error_and_high_forecast_tier(self):
        r=report([row()])
        a=r["by_market"]["PTS"]
        self.assertEqual(a["all"]["mean_signed_error_projection_minus_actual"],-5)
        self.assertEqual(a["high_forecast_tier"]["observations"],1)
        self.assertEqual(a["pregame_forecast_20pct_below_frozen_season_avg"]["observations"],1)
        self.assertFalse(r["conclusions"]["systematic_underprojection_proven"])
        self.assertFalse(r["conclusions"]["live_predictions_changed"])

    def test_high_season_baseline_catches_underestimated_star(self):
        x=row(stat="PRA",forecast=32.9,actual=49)
        x["season_average_challenger"]["season_average"]=42.4
        r=report([x])["by_market"]["PRA"]
        self.assertEqual(r["high_forecast_tier"]["observations"],0)
        self.assertEqual(r["high_frozen_season_baseline_tier"]["observations"],1)
        self.assertEqual(r["high_baseline_and_projection_20pct_below"]["observations"],1)

    def test_same_game_duplicate_book_does_not_double_count(self):
        one=row()
        late={**one,"bookmaker":"DraftKings","captured_at":"2026-11-06T22:00:00Z",
              "combined_projection":15}
        r=report([late,one])
        self.assertEqual(r["independent_markets"],1)
        self.assertEqual(r["by_market"]["PTS"]["all"]["mean_signed_error_projection_minus_actual"],-5)

    def test_no_future_result_and_invalid_row(self):
        pending={**row(),"status":"PENDING"}
        after={**row(pid="2"),"captured_at":"2026-11-07T01:00:00Z"}
        r=report([pending,after])
        self.assertEqual(r["independent_markets"],0)
        self.assertIsNone(r["by_market"]["AST"]["all"]["mae"])

    def test_forecast_tier_does_not_use_future_actual(self):
        r=report([row(pid="1",actual=60,forecast=20),row(pid="2",actual=0,forecast=30)])
        self.assertEqual(r["by_market"]["PTS"]["high_forecast_tier"]["observations"],1)
        self.assertEqual(r["by_market"]["PTS"]["other_forecast_tier"]["observations"],1)

    def test_absent_season_frozen_context_not_rebuilt(self):
        x=row()
        x.pop("season_average_challenger")
        r=report([x])
        self.assertEqual(r["data_quality"]["missing_frozen_current_season_baseline"],1)
        self.assertEqual(r["by_market"]["PTS"]["pregame_forecast_20pct_below_frozen_season_avg"]["observations"],0)

    def test_opponent_difference_is_descriptive_only(self):
        r=report([row()])
        d=r["by_market"]["PTS"]["opponent_vs_original"]
        self.assertEqual(d["mean_opponent_minus_original"],-4)
        self.assertFalse(r["conclusions"]["opponent_adjustment_causality_proven"])

    def test_frozen_minutes_risk_and_matchup_separate_strata(self):
        a=row(pid="1",forecast=30,actual=40)
        a["research_minutes_risk_v1"]={"needs_manual_review":True,
             "issues":["VOLATILE_RECENT_MINUTES"]}
        b=row(pid="2",forecast=29,actual=24)
        b["research_minutes_risk_v1"]={"needs_manual_review":False,"issues":[]}
        results=report([a,b])["by_market"]["PTS"]
        self.assertEqual(results["frozen_minutes_review_flagged"]["observations"],1)
        self.assertEqual(results["frozen_minutes_no_review_flags"]["observations"],1)
        self.assertEqual(results["opponent_model_1plus_below_original"]["observations"],2)

    def test_missing_opponent_forecast_not_faked(self):
        x=row()
        x["opponent_shadow_projection"]=None
        r=report([x])
        self.assertEqual(r["independent_markets"],0)
        self.assertEqual(r["data_quality"]["missing_eligible_forecast_or_actual"],1)

    def test_one_date_never_validates_global_correction(self):
        records=[row(pid=str(i),actual=40,forecast=20) for i in range(100)]
        r=report(records)
        self.assertEqual(r["overall"]["distinct_event_dates"],1)
        self.assertFalse(r["overall"]["sufficient_longitudinal_sample"])
        self.assertFalse(r["conclusions"]["ready_for_global_correction"])

    def test_multiple_markets_keep_distinct_units(self):
        r=report([row(stat="PTS",forecast=30,actual=40),row(stat="AST",pid="2",forecast=8,actual=10)])
        self.assertEqual(r["by_market"]["AST"]["all"]["mean_signed_error_projection_minus_actual"],-2)
        self.assertEqual(r["by_market"]["PTS"]["all"]["mean_signed_error_projection_minus_actual"],-10)

if __name__=="__main__":unittest.main()

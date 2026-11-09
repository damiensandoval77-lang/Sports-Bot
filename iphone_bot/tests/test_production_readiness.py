import datetime as dt
import unittest
from iphone_bot.production_readiness import check

NOW=dt.datetime(2026,11,9,18,0,tzinfo=dt.timezone.utc)
STAMP="2026-11-09T17:50:00+00:00"
GAME={"game":"Away @ Home","date_eastern":"2026-11-09",
      "start":"2026-11-10T00:00:00+00:00","game_state":"pre"}
def fixtures(now=NOW):
    return {
     "nba_schedule.json":{"generated_at":STAMP,"coverage_complete":True,
         "total_games":1,"games":[dict(GAME)]},
     "ai_projection_fallback.json":{"generated_at":STAMP,
         "status":"PREGAME_PROJECTIONS_NO_LINES",
         "predictions":[{"game":GAME["game"],"is_pregame_prediction":True}]},
     "nba_scoreboard_independent.json":{"generated_at":STAMP,
         "status":"NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE",
         "is_live_score_source":False,"games":[dict(GAME)]},
     "prizepicks_site.json":{"generated_at":STAMP,
         "status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES","complete_provider_board":True,
         "partial_board":False,"board_offers":[{"starts_at":GAME["start"],"is_demo":False}]},
     "nightly_grade_health.json":{"checked_at":STAMP,
         "game_date_eastern":"2026-11-08",
         "prizepicks_overdue":0,"paper_overdue":0,"capture_missing":False,
         "ai_forecasts_ungraded":0,
         "ai_forecast_accuracy_status":"AI_PRETIP_FORECASTS_GRADED"},
     "nba_player_tracking_independent.json":{},
     "data.json":{"updated_at":STAMP,"slate_events_checked":1,
                  "market_coverage_limited":False,
                  "picks":[{"game":GAME["game"],"line":18.5}]},
     "ai_comparisons.json":{"generated_at":STAMP,
                             "comparisons":[{"game":GAME["game"],"projection":19}]}
    }
class StrictProductionReadinessTests(unittest.TestCase):
    def test_healthy_complete_pregame_is_ready(self):
        r=check(NOW,fixtures())
        self.assertEqual(r["status"],"READY")
        self.assertTrue(r["ready_for_trustworthy_picks"])
        self.assertFalse(r["readiness_is_not_model_accuracy"] is False)

    def test_missing_projections_block(self):
        data=fixtures()
        data["ai_projection_fallback.json"]["predictions"]=[]
        r=check(NOW,data)
        self.assertEqual(r["status"],"BLOCKED")
        self.assertIn("UPCOMING_MATCHUPS_MISSING_AI",r["components"]["ai_forecasts"]["reasons"])

    def test_stale_partial_prizepicks_degrades_and_not_ready(self):
        data=fixtures()
        data["prizepicks_site.json"].update({
            "generated_at":"2026-11-09T09:24:00Z",
            "partial_board":True,"complete_provider_board":False})
        r=check(NOW,data)
        self.assertEqual(r["status"],"DEGRADED")
        self.assertFalse(r["ready_for_trustworthy_picks"])
        self.assertIn("STALE_SOURCE",r["components"]["prizepicks_lines"]["reasons"])
        self.assertIn("PARTIAL_PRIZEPICKS_PROVIDER_COVERAGE",
                      r["components"]["prizepicks_lines"]["reasons"])

    def test_tipoff_requires_live_scores_and_player_stats(self):
        data=fixtures()
        data["nba_schedule.json"]["games"][0]["start"]="2026-11-09T16:00:00Z"
        data["nba_schedule.json"]["games"][0]["game_state"]="in"
        r=check(NOW,data)
        self.assertEqual(r["status"],"BLOCKED")
        self.assertIn("scoreboard",r["blocking_components"])
        self.assertIn("live_player_stats",r["blocking_components"])
        self.assertIn("SCHEDULE_FALLBACK_NOT_LIVE_SCORES",
                      r["components"]["scoreboard"]["reasons"])

    def test_official_game_count_rejects_false_complete_seven_games(self):
        data=fixtures()
        data["verified_official_nba_fixtures.json"]={
            "official_expected_daily_counts":{"2026-11-09":8},
            "fixtures":[{"id":"0022600205","date_eastern":"2026-11-09",
                         "away_abbreviation":"WAS","home_abbreviation":"DET"}]}
        result=check(NOW,data)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertIn("OFFICIAL_NBA_SLATE_COUNT_MISMATCH",
                      result["components"]["schedule"]["reasons"])
        self.assertIn("OFFICIAL_NBA_MATCHUP_MISSING",
                      result["components"]["schedule"]["reasons"])

    def test_scoreboard_missing_even_one_scheduled_matchup_blocks(self):
        data=fixtures()
        data["nba_schedule.json"]["games"].append({
            "game":"Washington Wizards @ Detroit Pistons",
            "date_eastern":"2026-11-09","start":"2026-11-10T00:00:00Z",
            "game_state":"pre","away_abbreviation":"WAS","home_abbreviation":"DET"})
        data["nba_schedule.json"]["total_games"]=2
        result=check(NOW,data)
        self.assertIn("SCOREBOARD_MISSING_SCHEDULED_MATCHUPS",
                      result["components"]["scoreboard"]["reasons"])
        self.assertEqual(result["status"],"BLOCKED")

    def test_empty_games_cannot_claim_healthy(self):
        data=fixtures()
        data["nba_schedule.json"].update({"games":[],"total_games":0})
        self.assertEqual(check(NOW,data)["status"],"BLOCKED")

    def test_empty_production_pick_board_not_healthy(self):
        data=fixtures()
        data["data.json"]["picks"]=[]
        data["ai_comparisons.json"]["comparisons"]=[]
        r=check(NOW,data)
        self.assertEqual(r["status"],"DEGRADED")
        self.assertIn("NO_PUBLISHED_PROJECTION_VS_LINE_CARDS",
                      r["components"]["published_pick_cards"]["reasons"])

    def test_unchanged_stale_cards_fail_even_with_current_automatic_models(self):
        data=fixtures()
        data["data.json"]["updated_at"]="2026-11-07T23:51:00Z"
        data["ai_comparisons.json"]["generated_at"]="2026-11-07T23:52:00Z"
        r=check(NOW,data)
        self.assertIn("PUBLISHED_PICK_BOARD_STALE",
                      r["components"]["published_pick_cards"]["reasons"])

    def test_nightly_grade_incomplete_degrades(self):
        data=fixtures()
        data["nightly_grade_health.json"]["ai_forecasts_ungraded"]=24
        r=check(NOW,data)
        self.assertEqual(r["status"],"DEGRADED")
        self.assertIn("PREVIOUS_DAY_AI_GRADING_INCOMPLETE",
                      r["components"]["nightly_grades"]["reasons"])

    def test_verified_published_quick_join_reports_research_path_separately(self):
        data=fixtures()
        data["ai_prizepicks_quick_join_health.json"]={
            "status":"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
            "research_only":True,
            "generated_at":STAMP,"provider_generated_at":STAMP,
            "offers_matched":6,"matched_by_game":{GAME["game"]:6},
            "partial_provider_board":False,"source_coverage_complete":True}
        data["dashboard_html"]='fetchJSON("ai_prizepicks_quick_join.json") verifiedPublishedPrizePicksJoins('
        data["data.json"]["picks"]=[]
        data["ai_comparisons.json"]["comparisons"]=[]
        result=check(NOW,data)
        self.assertEqual(result["components"]["prizepicks_research_cards"]["state"],"READY")
        self.assertFalse(result["components"]["prizepicks_research_cards"]["required"])
        self.assertEqual(result["components"]["published_pick_cards"]["state"],"DEGRADED")
        self.assertFalse(result["ready_for_trustworthy_picks"])

    def test_quick_join_does_not_masquerade_as_live_if_feed_partial_or_ui_missing(self):
        data=fixtures()
        data["ai_prizepicks_quick_join_health.json"]={
            "status":"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
            "research_only":True,"generated_at":STAMP,
            "provider_generated_at":STAMP,"offers_matched":6,
            "matched_by_game":{GAME["game"]:6},
            "partial_provider_board":True,"source_coverage_complete":False}
        result=check(NOW,data)
        reasons=result["components"]["prizepicks_research_cards"]["reasons"]
        self.assertIn("PP_RESEARCH_SOURCE_PARTIAL",reasons)
        self.assertIn("DASHBOARD_PP_JOIN_HANDOFF_NOT_PRESENT",reasons)
        self.assertEqual(result["components"]["prizepicks_research_cards"]["state"],"DEGRADED")

    def test_missing_nightly_grade_report_degrades(self):
        data=fixtures()
        data["nightly_grade_health.json"]={}
        r=check(NOW,data)
        self.assertNotEqual(r["status"],"READY")

    def test_all_inputs_missing_fail_closed(self):
        r=check(NOW,{})
        self.assertEqual(r["status"],"BLOCKED")
        self.assertFalse(r["ready_for_trustworthy_picks"])

if __name__=="__main__":
    unittest.main()

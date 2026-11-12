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
         "partial_board":False,"board_coverage_scope":"NBA_ACTIVE_STANDARD_TIER_ONLY","board_offers":[{"starts_at":GAME["start"],"game":GAME["game"],"is_demo":False,"more_tier":"standard","less_tier":"standard"}]},
     "nightly_grade_health.json":{"checked_at":STAMP,
         "game_date_eastern":"2026-11-08",
         "prizepicks_overdue":0,"paper_overdue":0,"capture_missing":False,
         "ai_forecasts_ungraded":0,
         "ai_forecast_accuracy_status":"AI_PRETIP_FORECASTS_GRADED"},
     "tonight_capture_gradeability.json":{
         "status":"CAPTURE_VERIFIED","checked_at":STAMP,
         "game_date_eastern":"2026-11-09",
         "current_upcoming_coverage":{"status":"COMPLETE","missing_primary_offers":0,"issues":[],
             "games":[{"game":GAME["game"],"start":GAME["start"],"verified_current_offers":3,
                       "matched_primary_offers":3,"missing_primary_offers":0}]},
         "games":[{"game":GAME["game"],"issues":[]}],
         "summary":{"schedule_games":1,"games_with_saved_source_quotes":1,
                    "games_with_frozen_ai":1,"games_with_line_backed_models":1,
                    "total_line_backed":3,"total_standard_source_quotes":3,
                    "total_standard_markets_without_frozen_model":0,
                    "total_missing_primary_with_separate_research_receipt":0,
                    "total_missing_primary_without_any_ai_receipt":0}},
     "dames-picks/published_pick_settlement.json":{
         "checked_at":STAMP,"status":"READY",
         "counts":{"frozen_picks":3,"graded":0,"pending":3}},
     "dames-picks/browser_readiness.json":{
         "checked_at":STAMP,"status":"READY","browser_render_verified":True,
         "site_url":"https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/",
         "app_title":"Dame's Picks · NBA + NFL",
         "NBA":{"selected":"NBA","loaded":True,"rows":3,"rendered":3,"errors":[]},
         "NFL":{"selected":"NFL","loaded":True,"rows":3,"rendered":3,"errors":[]}},
     "nba_schedule_horizon_audit.json":{
         "status":"READY","checked_at":STAMP,"season_fixed_games":1200,
         "next_14_days":[{"date_eastern":(NOW.date()+dt.timedelta(days=n)).isoformat(),
                          "known_games":1,"games":[]} for n in range(14)],
         "next_two_days_reconciliation":{
             "2026-11-09":{"season_fixed_games":1,"daily_games":1,"missing":[]},
             "2026-11-10":{"season_fixed_games":1,"daily_games":1,"missing":[]}}},
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
        self.assertEqual(r["status"],"READY",r["components"])
        self.assertTrue(r["ready_for_trustworthy_picks"])
        self.assertFalse(r["readiness_is_not_model_accuracy"] is False)

    def test_released_season_calendar_required_even_if_today_props_exist(self):
        data=fixtures()
        data["nba_schedule_horizon_audit.json"]={}
        result=check(NOW,data)
        self.assertIn("season_calendar",result["blocking_components"])
        self.assertIn("FULL_SEASON_CALENDAR_NOT_VERIFIED",
                      result["components"]["season_calendar"]["reasons"])

    def test_known_missing_future_games_fail_schedule_readiness(self):
        data=fixtures()
        data["nba_schedule_horizon_audit.json"]["next_two_days_reconciliation"]["2026-11-09"]["missing"]=[
            {"game":"Away @ Home","id":"123"}]
        result=check(NOW,data)
        self.assertIn("KNOWN_TODAY_GAMES_MISSING",
                      result["components"]["season_calendar"]["reasons"])
        self.assertFalse(result["ready_for_trustworthy_picks"])

    def test_stale_horizon_report_cannot_claim_full_calendar(self):
        data=fixtures()
        data["nba_schedule_horizon_audit.json"]["checked_at"]="2026-11-08T10:00:00Z"
        result=check(NOW,data)
        self.assertIn("SEASON_HORIZON_AUDIT_STALE",
                      result["components"]["season_calendar"]["reasons"])

    def test_unscoped_complete_provider_never_makes_standard_board_green(self):
        data=fixtures()
        data["prizepicks_site.json"]["board_coverage_scope"]="UNVERIFIED_LEGACY_SCOPE"
        result=check(NOW,data)
        self.assertIn("STANDARD_ONLY_PROVIDER_SCOPE_UNVERIFIED",
                      result["components"]["prizepicks_lines"]["reasons"])
        self.assertFalse(result["ready_for_trustworthy_picks"])

    def test_fresh_provider_board_missing_entire_matchup_fails(self):
        data=fixtures()
        data["prizepicks_site.json"]["board_offers"][0]["game"]="Another @ Matchup"
        result=check(NOW,data)
        self.assertEqual(result["status"],"DEGRADED")
        self.assertIn("UPCOMING_MATCHUPS_WITHOUT_STANDARD_PROVIDER_LINES",
                      result["components"]["prizepicks_lines"]["reasons"])

    def test_alternate_tiers_cannot_masquerade_as_standard_coverage(self):
        data=fixtures()
        data["prizepicks_site.json"]["board_offers"][0]["more_tier"]="demon"
        result=check(NOW,data)
        self.assertIn("UPCOMING_MATCHUPS_WITHOUT_STANDARD_PROVIDER_LINES",
                      result["components"]["prizepicks_lines"]["reasons"])

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

    def test_legacy_sportsbook_outage_does_not_block_verified_prizepicks_site(self):
        data=fixtures()
        data["data.json"]["picks"]=[]
        data["ai_comparisons.json"]["comparisons"]=[]
        r=check(NOW,data)
        self.assertEqual(r["status"],"READY")
        self.assertFalse(r["components"]["published_pick_cards"]["required"])
        self.assertEqual(r["components"]["published_pick_cards"]["state"],"DEGRADED")
        self.assertIn("NO_PUBLISHED_PROJECTION_VS_LINE_CARDS",
                      r["components"]["published_pick_cards"]["reasons"])

    def test_unchanged_stale_cards_fail_even_with_current_automatic_models(self):
        data=fixtures()
        data["data.json"]["updated_at"]="2026-11-07T23:51:00Z"
        data["ai_comparisons.json"]["generated_at"]="2026-11-07T23:52:00Z"
        r=check(NOW,data)
        self.assertIn("PUBLISHED_PICK_BOARD_STALE",
                      r["components"]["published_pick_cards"]["reasons"])

    def test_raw_quote_not_modeled_is_visible_but_not_a_fabricated_pick(self):
        data=fixtures()
        capture=data["tonight_capture_gradeability.json"]
        capture["status"]="CAPTURE_INCOMPLETE"
        capture["games"][0]["issues"]=["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]
        capture["summary"].update(
            total_standard_markets_without_frozen_model=3,
            total_missing_primary_with_separate_research_receipt=2,
            total_missing_primary_without_any_ai_receipt=1)
        result=check(NOW,data)
        self.assertEqual(result["status"],"READY",result["components"])
        self.assertTrue(result["ready_for_trustworthy_picks"])
        self.assertFalse(result["components"]["unmodeled_provider_market_coverage"]["required"])
        self.assertIn("STANDARD_QUOTES_WITHOUT_PRIMARY_FROZEN_MODEL",
                      result["components"]["unmodeled_provider_market_coverage"]["reasons"])
        self.assertEqual(result["components"]["pregame_capture"]["state"],"READY")

    def test_current_missing_primary_remains_required_despite_research(self):
        data=fixtures()
        cur=data["tonight_capture_gradeability.json"]["current_upcoming_coverage"]
        cur.update(status="INCOMPLETE",missing_primary_offers=1)
        cur["games"][0].update(matched_primary_offers=2,missing_primary_offers=1)
        result=check(NOW,data)
        self.assertEqual(result["status"],"DEGRADED")
        self.assertTrue(result["components"]["current_primary_model_coverage"]["required"])
        self.assertIn("CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL",result["components"]["current_primary_model_coverage"]["reasons"])

    def test_absent_current_coverage_cannot_claim_ready(self):
        data=fixtures();data["tonight_capture_gradeability.json"].pop("current_upcoming_coverage")
        self.assertEqual(check(NOW,data)["components"]["current_primary_model_coverage"]["state"],"DEGRADED")

    def test_research_receipts_do_not_substitute_for_a_published_model(self):
        data=fixtures()
        capture=data["tonight_capture_gradeability.json"]
        capture["status"]="CAPTURE_INCOMPLETE"
        capture["games"][0]["issues"]=["PROVIDER_QUOTES_WITH_NO_FROZEN_LINE_BACKED_MODEL"]
        capture["summary"].update(
            games_with_line_backed_models=0,total_line_backed=0,
            total_standard_markets_without_frozen_model=3,
            total_missing_primary_with_separate_research_receipt=3,
            total_missing_primary_without_any_ai_receipt=0)
        result=check(NOW,data)
        self.assertNotEqual(result["status"],"READY")
        self.assertIn("UPCOMING_GAMES_WITHOUT_GRADEABLE_SAVED_PICKS",
                      result["components"]["pregame_capture"]["reasons"])

    def test_verified_final_missing_on_published_pick_blocks_ready(self):
        data=fixtures()
        data["dames-picks/published_pick_settlement.json"]["status"]="DEGRADED"
        result=check(NOW,data)
        self.assertIn("published_pick_settlement",result["degraded_components"])
        self.assertIn("PUBLISHED_FROZEN_PICKS_NOT_GRADEABLE",
                      result["components"]["published_pick_settlement"]["reasons"])

    def test_stale_published_gradeability_audit_blocks_ready(self):
        data=fixtures()
        data["dames-picks/published_pick_settlement.json"]["checked_at"]="2026-11-08T10:00:00Z"
        result=check(NOW,data)
        self.assertIn("PUBLISHED_GRADEABILITY_AUDIT_STALE",
                      result["components"]["published_pick_settlement"]["reasons"])

    def test_wrong_slate_and_stale_capture_cannot_claim_ready(self):
        data=fixtures()
        capture=data["tonight_capture_gradeability.json"]
        capture["checked_at"]="2026-11-08T11:00:00Z"
        capture["game_date_eastern"]="2026-11-08"
        result=check(NOW,data)
        self.assertEqual(result["status"],"DEGRADED")
        self.assertIn("CAPTURE_REPORT_STALE",result["components"]["pregame_capture"]["reasons"])
        self.assertIn("CAPTURE_REPORT_WRONG_SLATE_DATE",result["components"]["pregame_capture"]["reasons"])

    def test_inconsistent_capture_counts_fail_closed(self):
        data=fixtures()
        data["tonight_capture_gradeability.json"]["summary"].update(
            total_standard_markets_without_frozen_model=2,
            total_missing_primary_with_separate_research_receipt=2,
            total_missing_primary_without_any_ai_receipt=2)
        result=check(NOW,data)
        self.assertIn("CAPTURE_RECONCILIATION_INCONSISTENT",
                      result["components"]["pregame_capture"]["reasons"])

    def test_unified_browser_requires_both_leagues_even_if_nba_has_many_cards(self):
        data=fixtures()
        browser=data["dames-picks/browser_readiness.json"]
        browser["NBA"]["rendered"]=191
        browser["NFL"]["rendered"]=0
        result=check(NOW,data)
        self.assertFalse(result["ready_for_trustworthy_picks"])
        self.assertIn("NFL_PUBLIC_CARDS_NOT_RENDERED",
                      result["components"]["public_browser"]["reasons"])

    def test_unified_browser_missing_published_cards_blocks_ready(self):
        data=fixtures()
        data["dames-picks/browser_readiness.json"].update(
            status="DEGRADED",browser_render_verified=False)
        data["dames-picks/browser_readiness.json"]["NBA"]["rendered"]=0
        result=check(NOW,data)
        self.assertIn("public_browser",result["degraded_components"])
        self.assertIn("UNIFIED_BROWSER_NOT_VERIFIED",
                      result["components"]["public_browser"]["reasons"])
        self.assertIn("NBA_PUBLIC_CARDS_NOT_RENDERED",
                      result["components"]["public_browser"]["reasons"])

    def test_old_standalone_browser_cannot_make_unified_ready(self):
        data=fixtures()
        data["dames-picks/browser_readiness.json"]={}
        data["browser_card_probe.json"]={
           "status":"READY","browser_render_verified":True,
           "rendered_verified_standard_lines":999}
        result=check(NOW,data)
        self.assertFalse(result["ready_for_trustworthy_picks"])
        self.assertIn("UNIFIED_BROWSER_NOT_VERIFIED",
                      result["components"]["public_browser"]["reasons"])

    def test_stale_unified_browser_proof_fails(self):
        data=fixtures()
        data["dames-picks/browser_readiness.json"]["checked_at"]="2026-11-09T10:00:00Z"
        result=check(NOW,data)
        self.assertIn("UNIFIED_BROWSER_PROBE_STALE",
                      result["components"]["public_browser"]["reasons"])

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
        self.assertFalse(result["components"]["published_pick_cards"]["required"])
        # Passing comes from the separately verified full primary fixture and
        # public browser, not the research quick-join or legacy sportsbook.
        self.assertEqual(result["components"]["public_browser"]["state"],"READY")
        self.assertTrue(result["ready_for_trustworthy_picks"])

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

    def test_legacy_sportsbook_outage_does_not_hide_missing_prizepicks_browser(self):
        data=fixtures()
        data["data.json"]["picks"]=[]
        data["ai_comparisons.json"]["comparisons"]=[]
        data["dames-picks/browser_readiness.json"]["browser_render_verified"]=False
        result=check(NOW,data)
        self.assertEqual(result["status"],"DEGRADED")
        self.assertIn("public_browser",result["degraded_components"])

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

import datetime as dt
import unittest
from iphone_bot.app_release_gate import evaluate

NOW=dt.datetime(2026,11,10,23,30,tzinfo=dt.timezone.utc)
STAMP=NOW.isoformat()
def fixture():
    return {
        "unified_artifacts":{"checked_at":STAMP,"status":"READY","app":{"state":"READY"},"sports":{"NBA":{"state":"READY"},"NFL":{"state":"READY"}}},
        "public_unified_browser":{"checked_at":STAMP,"status":"READY","browser_render_verified":True,
            "site_url":"https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/",
            "NBA":{"selected":"NBA","loaded":True,"rendered":20},
            "NFL":{"selected":"NFL","loaded":True,"rendered":10}},
        "nba_production":{"checked_at":STAMP,"status":"READY","ready_for_trustworthy_picks":True,"components":{}},
        "nba_capture":{"checked_at":STAMP,"status":"CAPTURE_VERIFIED","summary":{"total_standard_markets_without_frozen_model":0}},
        "nba_grading":{"checked_at":STAMP,"status":"ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR",
                       "days":{"2026-11-09":{"pending":0,"captured":756,"accounted_for":756}}},
        "nfl_grading":{"official_grading_scope":"FROZEN_STANDARD_LINE_ONLY","standard_settled":60,"pending_picks":0,"standard_pending_picks":0},
        "published_pick_settlement":{"checked_at":STAMP,"status":"READY",
                                     "counts":{"frozen_picks":120,"graded":30,"pending":90}}
    }

class AppReleaseGateTests(unittest.TestCase):
    def test_all_green_starts_monitoring_not_certification(self):
        r=evaluate(fixture(),NOW)
        self.assertEqual(r["status"],"MONITORING")
        self.assertTrue(r["checks_passing"])
        self.assertFalse(r["release_certified"])
    def test_streak_requires_actual_sustained_72_hours(self):
        inp=fixture()
        prev={"checks_passing":True,"checked_at":(NOW-dt.timedelta(minutes=30)).isoformat(),
              "healthy_streak_started_at":(NOW-dt.timedelta(hours=72)).isoformat()}
        r=evaluate(inp,NOW,prev)
        self.assertEqual(r["status"],"CERTIFIED")
    def test_gap_resets_streak(self):
        prev={"checks_passing":True,"checked_at":(NOW-dt.timedelta(hours=3)).isoformat(),
              "healthy_streak_started_at":(NOW-dt.timedelta(hours=72)).isoformat()}
        self.assertEqual(evaluate(fixture(),NOW,prev)["status"],"MONITORING")
    def test_missing_primary_frozen_quote_blocks(self):
        inp=fixture()
        inp["nba_capture"]["status"]="CAPTURE_INCOMPLETE"
        inp["nba_capture"]["summary"]["total_standard_markets_without_frozen_model"]=154
        r=evaluate(inp,NOW)
        self.assertFalse(r["checks_passing"])
        self.assertIn("nba_capture",r["blocking_checks"])
    def test_unmodeled_raw_quotes_block_full_app_certification(self):
        inp=fixture()
        inp["nba_capture"]={
            "checked_at":STAMP,"status":"CAPTURE_INCOMPLETE",
            "issues":["Example @ Fixture: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"],
            "summary":{"schedule_games":1,"games_with_line_backed_models":1,
                       "total_standard_markets_without_frozen_model":139}}
        r=evaluate(inp,NOW)
        self.assertFalse(r["checks_passing"])
        self.assertIn("PRIMARY_STANDARD_COVERAGE_INCOMPLETE",r["checks"]["nba_capture"]["issues"])
    def test_uncaptured_game_blocks_app_even_with_good_other_picks(self):
        inp=fixture()
        inp["nba_capture"]={
            "checked_at":STAMP,"status":"CAPTURE_INCOMPLETE",
            "issues":["Example @ Fixture: PROVIDER_QUOTES_WITH_NO_FROZEN_LINE_BACKED_MODEL"],
            "summary":{"schedule_games":1,"games_with_line_backed_models":0,
                       "total_standard_markets_without_frozen_model":1}}
        r=evaluate(inp,NOW)
        self.assertIn("nba_capture",r["blocking_checks"])
        self.assertIn("REQUIRED_PREGAME_PICK_ARTIFACT_MISSING",
                      r["checks"]["nba_capture"]["issues"])
    def test_both_sports_must_render(self):
        inp=fixture()
        inp["public_unified_browser"]["NFL"]["rendered"]=0
        r=evaluate(inp,NOW)
        self.assertIn("NFL_BROWSER_MISSING_CARDS",r["checks"]["public_unified_browser"]["issues"])
    def test_published_pick_pending_final_blocks_app_release(self):
        inp=fixture()
        inp["published_pick_settlement"]["status"]="DEGRADED"
        inp["published_pick_settlement"]["issues"]={"VERIFIED_FINAL_NOT_APPLIED":11}
        result=evaluate(inp,NOW)
        self.assertIn("published_pick_settlement",result["blocking_checks"])
        self.assertFalse(result["release_certified"])

    def test_stale_reports_fail_even_if_flagged_ready(self):
        inp=fixture()
        inp["nba_production"]["checked_at"]=(NOW-dt.timedelta(hours=3)).isoformat()
        r=evaluate(inp,NOW)
        self.assertIn("MISSING_OR_STALE_REPORT",r["checks"]["nba_production"]["issues"])
    def test_nfl_historical_grades_require_standard_only(self):
        inp=fixture()
        inp["nfl_grading"]["official_grading_scope"]="ALL_TIERS"
        self.assertIn("NFL_STANDARD_GRADE_SCOPE_INVALID",
                      evaluate(inp,NOW)["checks"]["nfl_grading"]["issues"])
if __name__=="__main__":unittest.main()

class StandardOnlyReleaseTests(unittest.TestCase):
    def test_alternative_pending_does_not_block_complete_standard_scope(self):
        inp=fixture();inp["nfl_grading"].update(pending_picks=4,standard_pending_picks=0)
        self.assertEqual(evaluate(inp,NOW)["checks"]["nfl_grading"]["state"],"READY")
    def test_unknown_or_invalid_standard_count_does_not_pass(self):
        for value in [None,False,-1,"0",1]:
            inp=fixture();inp["nfl_grading"]["standard_pending_picks"]=value
            self.assertEqual(evaluate(inp,NOW)["checks"]["nfl_grading"]["state"],"DEGRADED")

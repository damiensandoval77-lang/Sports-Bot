"""Source freshness recovery must not consume credits or misstate readiness."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from iphone_bot.phase1_free_recovery import plan

NOW=dt.datetime(2026,11,10,19,0,tzinfo=dt.timezone.utc)
def put(root,name,doc):
    p=Path(root)/"docs"/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(doc))

class FreeRecoveryTests(unittest.TestCase):
    def test_stale_sources_replay_without_paid_collectors(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"nba_schedule.json",{"generated_at":"2026-11-10T12:00:00Z"})
            put(root,"ai_prizepicks_quick_join_health.json",{"status":"STALE_OR_UNVERIFIED_SOURCE"})
            put(root,"ai_forecast_grade_status.json",{"game_date_eastern":"2026-11-09","ungraded":136,"generated_at":"2026-11-10T12:00:00Z"})
            report=plan(root,NOW)
            flows=[x["workflow"] for x in report["dispatch_candidates"]]
            self.assertEqual(flows,["nba-schedule.yml","nba-prizepicks-site-publish.yml","grade_frozen_ai_forecasts.yml"])
            self.assertFalse(report["credit_spending_allowed"])
    def test_fresh_pregame_lines_allow_model_rebuild(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"nba_schedule.json",{"generated_at":"2026-11-10T18:00:00Z",
               "official_fixture_reconciliation":{"verified_daily_counts":{"2026-11-10":{"complete":True}}}})
            put(root,"ai_prizepicks_quick_join_health.json",{"generated_at":"2026-11-10T18:30:00Z",
                "status":"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
                "model_generated_at":"2026-11-10T10:00:00Z"})
            put(root,"prizepicks_model_input.json",{"status":"FRESH_AUTHENTIC_PRIZEPICKS_LINES",
                "is_live":True,"updated_at":"2026-11-10T18:30:00Z","picks":[{"line":25.5}]})
            flows=[x["workflow"] for x in plan(root,NOW)["dispatch_candidates"]]
            self.assertEqual(flows,["nba-prizepicks-ai-board.yml"])
    def test_old_lines_never_retrain(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"prizepicks_model_input.json",{"status":"FRESH_AUTHENTIC_PRIZEPICKS_LINES",
                "is_live":True,"updated_at":"2026-11-09T18:30:00Z","picks":[{"line":25.5}]})
            flows=[x["workflow"] for x in plan(root,NOW)["dispatch_candidates"]]
            self.assertNotIn("nba-prizepicks-ai-board.yml",flows)
    def test_stale_no_line_ai_dispatches_credit_free_projection_job(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"nba_schedule.json",{"generated_at":"2026-11-10T18:00:00Z",
                "games":[{"date_eastern":"2026-11-10","start":"2026-11-10T22:00:00Z"}],
                "official_fixture_reconciliation":{"verified_daily_counts":{"2026-11-10":{"complete":True}}}})
            put(root,"ai_projection_fallback.json",{"status":"PREGAME_PROJECTIONS_NO_LINES",
                "generated_at":"2026-11-10T12:00:00Z","predictions":[{"player":"Test"}]})
            flows=[x["workflow"] for x in plan(root,NOW)["dispatch_candidates"]]
            self.assertIn("nba-no-line-daily-projections.yml",flows)
            self.assertNotIn("nba-schedule.yml",flows)
    def test_fresh_ai_avoids_duplicate_model_generation(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"nba_schedule.json",{"generated_at":"2026-11-10T18:00:00Z",
                "games":[{"date_eastern":"2026-11-10","start":"2026-11-10T22:00:00Z"}],
                "official_fixture_reconciliation":{"verified_daily_counts":{"2026-11-10":{"complete":True}}}})
            put(root,"ai_projection_fallback.json",{"status":"PREGAME_PROJECTIONS_NO_LINES",
                "generated_at":"2026-11-10T18:50:00Z","predictions":[{"player":"Test"}]})
            flows=[x["workflow"] for x in plan(root,NOW)["dispatch_candidates"]]
            self.assertNotIn("nba-no-line-daily-projections.yml",flows)
    def test_verified_season_horizon_prevents_unneeded_schedule_dispatch(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"nba_schedule.json",{"generated_at":"2026-11-10T18:00:00Z",
                "games":[{"date_eastern":"2026-11-10","start":"2026-11-10T22:00:00Z"}]})
            put(root,"nba_schedule_horizon_audit.json",{"status":"READY",
                "checked_at":"2026-11-10T18:30:00Z",
                "next_two_days_reconciliation":{"2026-11-10":{
                    "season_fixed_games":1,"daily_games":1,"missing":[]}}})
            flows=[x["workflow"] for x in plan(root,NOW)["dispatch_candidates"]]
            self.assertNotIn("nba-schedule.yml",flows)
    def test_invalid_schedule_timestamp_does_not_crash_planner(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"nba_schedule.json",{"generated_at":"2026-11-10T18:00:00Z",
                "games":[{"start":"invalidZ"}]})
            flows=[x["workflow"] for x in plan(root,NOW)["dispatch_candidates"]]
            self.assertNotIn("nba-no-line-daily-projections.yml",flows)

    def test_fresh_model_and_provider_replay_stale_research_join(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"nba_schedule.json",{"generated_at":"2026-11-10T18:00:00Z",
                "games":[{"start":"2026-11-10T22:00:00Z"}]})
            put(root,"ai_projection_fallback.json",{"status":"PREGAME_PROJECTIONS_NO_LINES",
                "generated_at":"2026-11-10T18:50:00Z","predictions":[{"player":"Test"}]})
            put(root,"prizepicks_site.json",{"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
                "generated_at":"2026-11-10T18:40:00Z"})
            put(root,"ai_prizepicks_quick_join_health.json",{"generated_at":"2026-11-10T18:20:00Z",
                "status":"STALE_OR_UNVERIFIED_SOURCE","model_generated_at":"2026-11-10T10:00:00Z"})
            report=plan(root,NOW)
            flows=[r["workflow"] for r in report["dispatch_candidates"]]
            self.assertIn("publish_live_pp_ai_join.yml",flows)
            self.assertFalse(report["credit_spending_allowed"])
    def test_no_verified_provider_never_replays_research_join(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"nba_schedule.json",{"games":[{"start":"2026-11-10T22:00:00Z"}]})
            put(root,"ai_projection_fallback.json",{"status":"PREGAME_PROJECTIONS_NO_LINES",
                "generated_at":"2026-11-10T18:50:00Z","predictions":[{"player":"Test"}]})
            put(root,"prizepicks_site.json",{"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
                "generated_at":"2026-11-10T11:00:00Z"})
            flows=[r["workflow"] for r in plan(root,NOW)["dispatch_candidates"]]
            self.assertNotIn("publish_live_pp_ai_join.yml",flows)

if __name__=="__main__":unittest.main()

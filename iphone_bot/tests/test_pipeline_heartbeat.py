"""Tests for deployed-site pipeline heartbeat, failed-run discovery and data gaps."""
import datetime as dt
import unittest
from iphone_bot.pipeline_heartbeat import evaluate
NOW=dt.datetime(2026,11,11,23,30,tzinfo=dt.timezone.utc)
def time(**kw):return (NOW+dt.timedelta(**kw)).isoformat()
GAME="Miami Heat @ Utah Jazz"
def site(start=None,snapshot=None,ledger=None,model=None):
    start=start or time(minutes=30)
    return {"prizepicks.json":{"generated_at":time(minutes=-15),"board_offers":[{"game":GAME,"starts_at":start,"more_tier":"standard","less_tier":"standard"}]},
            "prizepicks_site.json":{"generated_at":snapshot or time(minutes=-10),"board_offers":[{"game":GAME,"starts_at":start,"more_tier":"standard","less_tier":"standard"}]},
            "lagged_matchup_all_market_ledger.json":{"records":ledger or []},
            "lagged_matchup_live_all_markets.json":model or {},
            "nba_schedule.json":{"games":[{"game":GAME,"start":start}]},
            "nba_scoreboard_independent.json":{},"nba_player_tracking_independent.json":{}}
def stage(r,name):return next(x for x in r["stages"] if x["stage"]==name)
class Heartbeat(unittest.TestCase):
    def test_old_published_lines_fail(self):
        self.assertEqual(stage(evaluate(NOW,site(snapshot=time(hours=-6))),"lines_publish")["status"],"FAIL")
    def test_missing_picks_three_hours_before_tip_fail(self):
        self.assertEqual(stage(evaluate(NOW,site()),"picks_frozen")["status"],"FAIL")
    def test_missing_picks_five_hours_before_tip_warn(self):
        self.assertEqual(stage(evaluate(NOW,site(start=time(hours=5))),"picks_frozen")["status"],"WARN")
    def test_matching_saved_picks_good(self):
        start=time(minutes=30)
        self.assertEqual(stage(evaluate(NOW,site(start=start,ledger=[{"game":GAME,"start":start}])),"picks_frozen")["status"],"OK")
    def test_older_matchup_does_not_count(self):
        self.assertEqual(stage(evaluate(NOW,site(ledger=[{"game":GAME,"start":time(days=-20)}])),"picks_frozen")["status"],"FAIL")
    def test_model_timestamp_cannot_hide_missing_games(self):
        report=evaluate(NOW,site(model={"generated_at":time(minutes=-2)}))
        self.assertEqual(stage(report,"picks_frozen")["status"],"FAIL")
        self.assertTrue(stage(report,"picks_frozen")["evidence"]["missing"])
    def test_missing_game_alert_includes_exact_model_withhold_reason(self):
        diagnostic={"observed_provider_quote_rows":78,"verified_standard_offers":24,
                    "frozen_forecasts":0,"excluded":{"INJURY_AFFECTED_PROJECTION_WITHHELD":24}}
        model={"generated_at":time(minutes=-2),"game_diagnostics":{GAME:diagnostic}}
        report=stage(evaluate(NOW,site(model=model)),"picks_frozen")
        self.assertEqual(report["status"],"FAIL")
        self.assertEqual(report["evidence"]["excluded_by_game"][GAME]["frozen_forecasts"],0)
        self.assertEqual(report["evidence"]["excluded_by_game"][GAME]["excluded"],diagnostic["excluded"])

    def test_schedule_without_any_source_quotes_must_not_be_green(self):
        s=site()
        s["prizepicks.json"]["board_offers"]=[]
        s["prizepicks_site.json"]["board_offers"]=[]
        report=evaluate(NOW,s)
        self.assertEqual(stage(report,"lines_coverage")["status"],"FAIL")
        self.assertIsNone(stage(report,"lines_coverage")["recovery_workflow"])
        self.assertEqual(report["overall"],"FAIL")

    def test_verified_provider_tip_shift_does_not_fake_missing_line(self):
        s=site()
        offset=time(minutes=40)
        for f in ("prizepicks.json","prizepicks_site.json"):
            s[f]["board_offers"][0]["starts_at"]=offset
        report=evaluate(NOW,s)
        self.assertEqual(stage(report,"lines_coverage")["status"],"OK")
        self.assertEqual(stage(report,"picks_frozen")["status"],"FAIL")
        s["lagged_matchup_all_market_ledger.json"]["records"]=[
            {"game":GAME,"start":offset,"grade":"PENDING"}]
        report=evaluate(NOW,s)
        self.assertEqual(stage(report,"picks_frozen")["status"],"OK")

    def test_yesterday_matchup_never_counts_as_todays_standard_lines(self):
        s=site()
        for f in ("prizepicks.json","prizepicks_site.json"):
            s[f]["board_offers"][0]["starts_at"]=time(days=-1)
        report=evaluate(NOW,s)
        self.assertEqual(stage(report,"lines_coverage")["status"],"FAIL")

    def test_missing_source_quotes_early_in_day_is_a_warning_not_fake_zero(self):
        s=site(start=time(hours=5))
        s["prizepicks.json"]["board_offers"]=[]
        s["prizepicks_site.json"]["board_offers"]=[]
        report=evaluate(NOW,s)
        self.assertEqual(stage(report,"lines_coverage")["status"],"WARN")

    def test_partial_primary_frozen_market_is_not_hidden_by_game_coverage(self):
        s=site()
        start=time(minutes=30)
        s["lagged_matchup_all_market_ledger.json"]["records"]=[{"game":GAME,"start":start,"grade":"PENDING"}]
        s["tonight_capture_gradeability.json"]={
            "game_date_eastern":"2026-11-11","status":"CAPTURE_INCOMPLETE",
            "games":[{"game":GAME,"start":start,
                      "standard_player_stat_markets_never_primary_frozen":11,
                      "missing_primary_without_any_ai_receipt":3}]}
        s["nba_schedule.json"]["games"][0]["date_eastern"]="2026-11-11"
        report=evaluate(NOW,s)
        self.assertEqual(stage(report,"picks_frozen")["status"],"OK")
        cap=stage(report,"capture_integrity")
        self.assertEqual(cap["status"],"FAIL")
        self.assertEqual(cap["evidence"]["without_any_ai_receipt"],3)

    def test_incomplete_pretip_capture_never_backdates_after_tip(self):
        s=site(start=time(minutes=-70))
        report=evaluate(NOW,s)
        picked=stage(report,"picks_frozen")
        self.assertEqual(picked["status"],"FAIL")
        self.assertTrue(picked["evidence"]["too_late_to_capture"])
        self.assertIsNone(picked["recovery_workflow"])

    def test_espn_unavailable_during_possible_live_game_is_not_green(self):
        s=site(start=time(minutes=-75))
        # Missing official ESPN response is uncertainty; avoid a false OK.
        report=evaluate(NOW,s,espn=None)
        self.assertEqual(stage(report,"live_scores")["status"],"WARN")
        self.assertEqual(stage(report,"live_players")["status"],"WARN")

    def test_scoreboard_live_game_with_missing_player_rows_is_failure(self):
        s=site(start=time(minutes=-75))
        s["nba_scoreboard_independent.json"]={
            "generated_at":time(minutes=-3),
            "games":[{"game":GAME,"game_state":"in"}]}
        report=evaluate(NOW,s)
        self.assertEqual(stage(report,"live_players")["status"],"FAIL")

    def test_fresh_feed_wrapper_does_not_hide_old_retained_live_game(self):
        s=site(start=time(minutes=-75))
        s["nba_scoreboard_independent.json"]={
            "generated_at":time(minutes=-3),
            "games":[{"game":GAME,"game_state":"in"}]}
        s["nba_player_tracking_independent.json"]={
            "captured_at":time(minutes=-3),
            "status":"PARTIAL_NBA_PLAYER_BOXSCORES",
            "games":[{"game":GAME,"observed_at":time(minutes=-48),
                      "player_rows":[{"player":"A","PTS":12}]}]}
        row=stage(evaluate(NOW,s),"live_players")
        self.assertEqual(row["status"],"FAIL")
        self.assertIn(GAME,row["evidence"]["stale_game_observations"])

    def test_new_per_game_live_observation_can_satisfy_live_coverage(self):
        s=site(start=time(minutes=-75))
        s["nba_scoreboard_independent.json"]={
            "generated_at":time(minutes=-3),
            "games":[{"game":GAME,"game_state":"in"}]}
        s["nba_player_tracking_independent.json"]={
            "captured_at":time(minutes=-3),
            "games":[{"game":GAME,"observed_at":time(minutes=-3),
                      "player_rows":[{"player":"A","PTS":12}]}]}
        row=stage(evaluate(NOW,s,espn={"events":[]}),"live_players")
        self.assertEqual(row["status"],"OK")

    def test_missing_schedule_fails_even_when_no_markets_expected(self):
        self.assertEqual(stage(evaluate(NOW,{}),"schedule")["status"],"FAIL")

    def test_overdue_pending_requires_settlement(self):
        r={"game":GAME,"start":time(hours=-10),"grade":"PENDING"}
        self.assertEqual(stage(evaluate(NOW,site(ledger=[r])),"settlement")["status"],"FAIL")
    def test_alert_evidence_survives_disabled_github_issues(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[2]/".github/workflows/pipeline-heartbeat.yml").read_text()
        self.assertIn("GITHUB_STEP_SUMMARY",workflow)
        self.assertIn("gh api \"repos/$GH_REPO\" --jq '.has_issues'",workflow)
        self.assertIn("GitHub Issues disabled or unavailable",workflow)
        self.assertIn('steps.health.outputs.code != \'0\'',workflow)

    def test_missing_feeds_report_non_ok(self):
        self.assertEqual(evaluate(NOW,{})["overall"],"FAIL")
if __name__=="__main__":unittest.main()

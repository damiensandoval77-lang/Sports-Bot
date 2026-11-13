import unittest
from iphone_bot.verify_unified_dames_browser import assess

class UnifiedBrowserAssessmentTests(unittest.TestCase):
    def test_both_sports_rendered(self):
        result=assess({"selected":"NBA","loaded":True,"rows":12,"rendered":4,"live_expected":0},
                      {"selected":"NFL","loaded":True,"rows":18,"rendered":5,"live_expected":0},[],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertEqual(result["status"],"READY")
    def test_nfl_missing_is_not_hidden_by_nba(self):
        result=assess({"selected":"NBA","loaded":True,"rows":12,"rendered":4,"live_expected":0},
                      {"selected":"NFL","loaded":True,"rows":0,"rendered":0,"live_expected":0},[],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertIn("NFL_NO_SAVED_RECORDS",result["reasons"])
    def test_old_single_sport_page_rejected(self):
        result=assess({"selected":"NBA","loaded":True,"rows":1,"rendered":1,"live_expected":0},
                      {"selected":"NFL","loaded":True,"rows":1,"rendered":1,"live_expected":0},[],
                      app_title="Sports-Bot · NBA Prop Board")
        self.assertIn("NOT_UNIFIED_APP",result["reasons"])
    def test_partial_nfl_shard_is_degraded_even_when_cards_show(self):
        result=assess({"selected":"NBA","loaded":True,"rows":12,"rendered":4,"live_expected":0,"errors":[]},
                      {"selected":"NFL","loaded":True,"rows":18,"rendered":5,"live_expected":0,
                       "errors":["NFL feed partially loaded"]},[],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertIn("NFL_REQUIRED_FEED_ERRORS",result["reasons"])
    def test_missing_nba_ledger_not_masked_by_archived_quote_cards(self):
        result=assess({"selected":"NBA","loaded":True,"rows":12,"rendered":4,"live_expected":0,
                       "errors":["NBA frozen ledger unavailable"]},
                      {"selected":"NFL","loaded":True,"rows":18,"rendered":5,"live_expected":0},[],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertIn("NBA_REQUIRED_FEED_ERRORS",result["reasons"])
    def test_started_nba_missing_live_totals_fails_despite_archive_cards(self):
        r=assess({"selected":"NBA","loaded":True,"rows":697,"rendered":697,
                  "live_expected":1,"live_missing":1,"score_missing":1,
                  "player_missing":1,"errors":[]},
                 {"selected":"NFL","loaded":True,"rows":364,"rendered":364,
                  "live_expected":0},[],app_title="Dame's Picks · NBA + NFL")
        self.assertEqual(r["status"],"DEGRADED")
        self.assertIn("NBA_STARTED_GAMES_MISSING_LIVE_DATA",r["reasons"])
        self.assertIn("NBA_STARTED_GAMES_MISSING_SCORES",r["reasons"])
        self.assertIn("NBA_STARTED_GAMES_MISSING_PLAYERS",r["reasons"])

    def test_active_leagues_with_fresh_scores_and_players_can_pass(self):
        r=assess({"selected":"NBA","loaded":True,"rows":100,"rendered":100,
                  "live_expected":2,"live_missing":0,"score_missing":0,
                  "player_missing":0},
                 {"selected":"NFL","loaded":True,"rows":100,"rendered":100,
                  "live_expected":1,"live_missing":0,"score_missing":0,
                  "player_missing":0},[],app_title="Dame's Picks · NBA + NFL")
        self.assertEqual(r["status"],"READY")

    def test_missing_live_contract_must_not_pass(self):
        r=assess({"selected":"NBA","loaded":True,"rows":10,"rendered":10},
                 {"selected":"NFL","loaded":True,"rows":10,"rendered":10,
                  "live_expected":0},[],app_title="Dame's Picks · NBA + NFL")
        self.assertIn("NBA_LIVE_COVERAGE_NOT_TESTED",r["reasons"])

    def test_js_errors_are_not_silently_hidden(self):
        result=assess({"selected":"NBA","loaded":True,"rows":1,"rendered":1,"live_expected":0},
                      {"selected":"NFL","loaded":True,"rows":1,"rendered":1,"live_expected":0},["Cannot read properties of null"],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertIn("UNHANDLED_JS_ERRORS",result["reasons"])
    def test_probe_waits_for_completed_browser_direct_refresh_before_assessment(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1] / "verify_unified_dames_browser.py").read_text()
        self.assertIn("await liveTick(true)",source)
        self.assertIn("page.wait_for_function(\"() => !state.liveBusy\"",source)
        self.assertLess(source.index("await liveTick(true)"),source.index("for sport in (\"NBA\",\"NFL\")"))
        self.assertIn('report["browser_direct_probe"]=direct',source)

if __name__=="__main__":unittest.main()

import unittest
from iphone_bot.verify_unified_dames_browser import assess

class UnifiedBrowserAssessmentTests(unittest.TestCase):
    def test_both_sports_rendered(self):
        result=assess({"selected":"NBA","loaded":True,"rows":12,"rendered":4},
                      {"selected":"NFL","loaded":True,"rows":18,"rendered":5},[],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertEqual(result["status"],"READY")
    def test_nfl_missing_is_not_hidden_by_nba(self):
        result=assess({"selected":"NBA","loaded":True,"rows":12,"rendered":4},
                      {"selected":"NFL","loaded":True,"rows":0,"rendered":0},[],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertIn("NFL_NO_SAVED_RECORDS",result["reasons"])
    def test_old_single_sport_page_rejected(self):
        result=assess({"selected":"NBA","loaded":True,"rows":1,"rendered":1},
                      {"selected":"NFL","loaded":True,"rows":1,"rendered":1},[],
                      app_title="Sports-Bot · NBA Prop Board")
        self.assertIn("NOT_UNIFIED_APP",result["reasons"])
    def test_partial_nfl_shard_is_degraded_even_when_cards_show(self):
        result=assess({"selected":"NBA","loaded":True,"rows":12,"rendered":4,"errors":[]},
                      {"selected":"NFL","loaded":True,"rows":18,"rendered":5,
                       "errors":["NFL feed partially loaded"]},[],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertIn("NFL_REQUIRED_FEED_ERRORS",result["reasons"])
    def test_missing_nba_ledger_not_masked_by_archived_quote_cards(self):
        result=assess({"selected":"NBA","loaded":True,"rows":12,"rendered":4,
                       "errors":["NBA frozen ledger unavailable"]},
                      {"selected":"NFL","loaded":True,"rows":18,"rendered":5},[],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertIn("NBA_REQUIRED_FEED_ERRORS",result["reasons"])
    def test_js_errors_are_not_silently_hidden(self):
        result=assess({"selected":"NBA","loaded":True,"rows":1,"rendered":1},
                      {"selected":"NFL","loaded":True,"rows":1,"rendered":1},["Cannot read properties of null"],
                      app_title="Dame's Picks · NBA + NFL")
        self.assertIn("UNHANDLED_JS_ERRORS",result["reasons"])
if __name__=="__main__":unittest.main()

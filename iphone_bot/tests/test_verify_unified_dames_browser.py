import unittest
from iphone_bot.verify_unified_dames_browser import assess, assess_live_order, assess_confidence, assess_pace

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



class LiveOrderTests(unittest.TestCase):
    def observation(self, cards):
        return {"sport":"NFL","selected":"NFL","mode":"live","expected_ids":[c["id"] for c in cards],"cards":cards}
    def test_live_first_and_upcoming_chronological(self):
        cards=[{"id":"live","state":"in","start":"2026-11-15T20:00:00Z"},
               {"id":"tomorrow","state":"scheduled","start":"2026-11-15T14:30:00Z"},
               {"id":"nextweek","state":"scheduled","start":"2026-11-22T18:00:00Z"}]
        self.assertEqual(assess_live_order(self.observation(cards)),[])
        cards[1:]=reversed(cards[1:])
        self.assertIn("LIVE_FIXTURES_OUT_OF_ORDER",assess_live_order(self.observation(cards)))
    def test_stale_board_cards_cannot_pass(self):
        self.assertIn("LIVE_FIXTURE_RENDER_MISMATCH",assess_live_order({"expected_ids":["NFL|1"],"cards":[]}))
    def test_duplicate_and_missing_fixture_fail(self):
        self.assertIn("LIVE_FIXTURE_RENDER_MISMATCH",assess_live_order({"expected_ids":["a","b"],"cards":[{"id":"a"},{"id":"a"}]}))
    def test_empty_slate_is_valid(self):
        self.assertEqual(assess_live_order(self.observation([])),[])
    def test_unknown_time_last_in_state(self):
        cards=[{"id":"a","state":"scheduled","start":None},{"id":"b","state":"scheduled","start":"2026-11-15T14:30:00Z"}]
        self.assertIn("LIVE_FIXTURES_OUT_OF_ORDER",assess_live_order(self.observation(cards)))
    def test_warm_reload_same_page_is_exercised(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/"verify_unified_dames_browser.py").read_text()
        self.assertIn('host.reload(wait_until="domcontentloaded"',source)
        self.assertIn('"WARM_RELOAD"',source)

    def test_wrong_view_empty_slate_fails(self):
        self.assertIn("LIVE_VIEW_NOT_SELECTED",assess_live_order({"sport":"NFL","selected":"NBA","mode":"tracker","expected_ids":[],"cards":[]}))

class ConfidenceBrowserTests(unittest.TestCase):
    def obs(self):
        return dict(eligible_count=1,viewport_width=390,overflow=0,estimates=[80,62],
          card=dict(line="6.5",projection="5.5",direction="UNDER",estimate="~62%"),
          detail=dict(line="6.5",projection="5.5",direction="UNDER",estimate="~62%",note="Limited. Applied Nov 14. Raw saved confidence 75%."),
          expected_estimate="~62%",expected_raw="75%",expected_applied="Nov 14",validation_notice="Limited.",grade_before="PENDING",grade_after="PENDING")
    def test_correct_display(self):
        self.assertEqual(assess_confidence(self.obs()),[])
    def test_changed_estimate_pick_grade(self):
        o=self.obs();o['detail'].update(estimate="75%",direction="OVER");o['grade_after']='GRADED'
        r=assess_confidence(o)
        for x in ['NBA_CORRECTION_DISPLAY_MISMATCH','NBA_CORRECTION_CHANGED_PICK','NBA_CORRECTION_CHANGED_GRADE']:self.assertIn(x,r)
    def test_provenance_order_layout(self):
        o=self.obs();o['detail']['note']='';o.update(estimates=[62,80],overflow=20)
        r=assess_confidence(o)
        for x in ['NBA_CORRECTION_PROVENANCE_MISSING','NBA_BOARD_CONFIDENCE_ORDER','NBA_CONFIDENCE_PHONE_LAYOUT']:self.assertIn(x,r)
    def test_no_eligible_is_not_false_failure(self):
        self.assertEqual(assess_confidence(dict(eligible_count=0,viewport_width=390,overflow=0,estimates=[])),[])

if __name__=="__main__":unittest.main()



class PaceAssessmentTests(unittest.TestCase):
    def obs(self, expected=0, rows=None, empty=True):
        return dict(viewport_width=390,overflow=0,expected_rows=expected,rows=rows or [],empty_notice=empty)
    def test_no_quotes_is_not_missing_label(self):
        self.assertEqual(assess_pace(self.obs()),[])
    def test_missing_expected_prop_still_fails(self):
        self.assertIn('LIVE_PACE_PROP_RENDER_MISMATCH',assess_pace(self.obs(1)))
    def test_empty_notice_required(self):
        self.assertIn('LIVE_PACE_EMPTY_STATE_MISSING',assess_pace(self.obs(empty=False)))
    def test_missing_label_on_real_prop_fails(self):
        self.assertIn('LIVE_PACE_LABEL_MISSING',assess_pace(self.obs(1,[{'text':'Actual 2'}])))
    def test_available_and_unavailable_labels_pass(self):
        for label in ('Game-clock pace (estimate) 18','Pace unavailable: clock missing'):
            self.assertEqual(assess_pace(self.obs(1,[{'text':label}])),[])
    def test_missing_expectation_fails(self):
        o=self.obs();del o['expected_rows']
        self.assertIn('LIVE_PACE_COVERAGE_NOT_TESTED',assess_pace(o))

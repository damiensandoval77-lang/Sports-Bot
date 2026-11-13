import unittest
from datetime import datetime,timezone
from iphone_bot.prizepicks_research_ledger import freeze,settle,summarize
NOW=datetime(2026,11,8,23,0,tzinfo=timezone.utc)
SOURCE={"status":"PRIZEPICKS_AI_RESEARCH_ONLY_NOT_SPORTSBOOK_ODDS",
        "generated_at":"2026-11-08T20:00:00Z",
        "comparisons":[{
          "provider_projection_id":"offer42","player_id":"203999","player":"Test Player",
          "team":"BOS","game":"Boston Celtics @ Charlotte Hornets",
          "start":"2026-11-08T21:00:00Z","captured_at":"2026-11-08T20:01:00Z",
          "observed_at":"2026-11-08T20:00:00Z",
          "stat":"AST","line":5.5,"combined_projection":7.2,
          "original_projection":7.0,"opponent_aware_projection":7.4}]}
GAME={"id":"203999","team":"BOS","opponent":"CHA","date":"2026-11-08",
      "AST":8,"REB":3,"PTS":18,"PRA":29,"MIN":32}
class ResearchLedgerTests(unittest.TestCase):
 def test_only_freezes_eligible_pretip_and_deduplicates(self):
    initial=freeze({"records":[]},SOURCE)
    self.assertEqual(initial["new"],1)
    duplicate=freeze({"records":initial["records"]},SOURCE)
    self.assertEqual(duplicate["new"],0)
    self.assertEqual(len(duplicate["records"]),1)
 def test_rejects_late_capture(self):
    late={**SOURCE,"comparisons":[{**SOURCE["comparisons"][0],
          "captured_at":"2026-11-08T21:10:00Z"}]}
    self.assertEqual(freeze({"records":[]},late)["new"],0)
 def test_actual_grade_respects_opponent_and_date(self):
    saved=freeze({"records":[]},SOURCE)
    wrong=settle(saved,[{**GAME,"opponent":"NYK"}],NOW)
    self.assertEqual(wrong["records"][0]["status"],"PENDING")
    result=settle(saved,[GAME],NOW)
    self.assertEqual(result["records"][0]["status"],"SETTLED")
    self.assertEqual(result["records"][0]["result"],"WIN")
    again=settle(result,[{**GAME,"AST":0}],NOW)
    self.assertEqual(again["records"][0]["actual"],8)
    self.assertEqual(summarize(result,NOW)["all_tiers_research_by_market"]["AST"]["wins"],1)
    self.assertEqual(summarize(result,NOW)["by_market"]["AST"]["graded_lines"],0)
 def test_alternate_thresholds_not_counted_as_independent_hits(self):
    rows=[]
    for i,line in enumerate((3.5,5.5,7.5)):
        v={**SOURCE["comparisons"][0],
           "provider_projection_id":"different"+str(i),"line":line,
           "source":"independent_prizepicksapi_com",
           "more_tier":("goblin","standard","demon")[i],
           "less_tier":("goblin","standard","demon")[i]}
        rows.append(v)
    frozen=freeze({"records":[]},{**SOURCE,"comparisons":rows})
    graded=settle(frozen,[GAME],NOW)
    summary=summarize(graded,NOW)
    self.assertEqual(summary["settled"],3)
    self.assertEqual(summary["independent_player_market_count"],1)
    self.assertEqual(summary["independent_settled_center_lines"],1)
    self.assertEqual(summary["independent_by_market"]["AST"]["graded"],1)
    self.assertEqual(summary["independent_by_market"]["AST"]["wins"],1)
    self.assertEqual(summary["verified_quote_tier_counts"],
                     {"standard":1,"goblin":1,"demon":1,"unverified":0})
    self.assertEqual(summary["all_tiers_research_by_market"]["AST"]["graded_lines"],3)
 def test_joint_v3_v2_shadows_are_frozen_and_graded(self):
    src={**SOURCE,"comparisons":[{
      **SOURCE["comparisons"][0],
      "minutes_v3_research":{
         "status":"PREGAME_MINUTES_V3_RESEARCH",
         "expected_minutes":31.5,"last_prior_date":"2026-11-07"},
      "minutes_v2_research_baseline":30,
      "source":"independent_prizepicksapi_com",
      "more_tier":"standard","less_tier":"standard",
      "opportunity_v2_research":{"markets":{"AST":{
        "status":"PREGAME_OPPORTUNITY_V2_RESEARCH","projection":7.5,
        "last_prior_game":"2026-11-07",
        "source_kind":"BOX_SCORE_RATE_PROXY"}}}
    }]}
    stored=freeze({"records":[]},src)
    self.assertEqual(stored["records"][0]["opportunity_v2_research"]["markets"]["AST"]["projection"],7.5)
    graded=settle(stored,[GAME],NOW)
    summary=summarize(graded,NOW)["minutes_v3_opportunity_v2_paired"]["by_market"]["AST"]
    self.assertEqual(summary["paired"],1)
    self.assertEqual(summary["challenger_wins"],1)
    self.assertEqual(summary["tracked_chances_samples"],0)
    self.assertFalse(summarize(graded,NOW)["verified_ev"])
 def test_absent_original_shadows_do_not_get_retrospective_grades(self):
    sample=settle(freeze({"records":[]},SOURCE),[GAME],NOW)
    result=summarize(sample,NOW)["minutes_v3_opportunity_v2_paired"]["by_market"]["AST"]
    self.assertEqual(result["paired"],0)
 def test_missing_final_does_not_invent_grades(self):
    saved=freeze({"records":[]},SOURCE)
    result=settle(saved,[],NOW)
    self.assertEqual(result["records"][0]["status"],"PENDING")
 def test_median_of_alternatives_never_counts_as_standard(self):
    rows=[]
    for i,line in enumerate((2.5,5.5,8.5)):
        rows.append({**SOURCE["comparisons"][0],
            "provider_projection_id":"alt"+str(i),"line":line})
    settled=settle(freeze({"records":[]},{**SOURCE,"comparisons":rows}),[GAME],NOW)
    report=summarize(settled,NOW)
    self.assertEqual(report["independent_by_market"]["AST"]["graded"],0)
    self.assertIsNone(report["independent_by_market"]["AST"]["hit_rate"])
    self.assertEqual(report["verified_quote_tier_counts"]["unverified"],3)
    self.assertEqual(report["all_tiers_research_by_market"]["AST"]["graded_lines"],3)

 def test_historical_legacy_tier_requires_exact_provider_archive(self):
    base=settle(freeze({"records":[]},SOURCE),[GAME],NOW)
    original=base["records"][0]
    quote={"id":"offer42","player":"Test Player","team":"BOS",
       "game":"Boston Celtics @ Charlotte Hornets","stat":"AST",
       "line":5.5,"starts_at":"2026-11-08T21:00:00Z",
       "observed_at":"2026-11-08T20:00:00Z",
       "source_generated_at":"2026-11-08T20:00:10Z",
       "source":"independent_prizepicksapi_com","is_demo":False,
       "tier":"standard","more_tier":"standard","less_tier":"standard"}
    archive={"status":"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE",
             "quotes":[quote]}
    report=summarize(base,NOW,archive)
    self.assertEqual(report["independent_by_market"]["AST"]["graded"],1)
    self.assertEqual(report["verified_quote_tier_counts"]["standard"],1)
    bad={**archive,"quotes":[{**quote,"tier":"demon","more_tier":"demon",
                              "less_tier":"demon"}]}
    self.assertEqual(summarize(base,NOW,bad)["independent_by_market"]["AST"]["graded"],0)
    conflicting={**archive,"quotes":[quote,{**quote,"line":6.5}]}
    self.assertEqual(summarize(base,NOW,conflicting)["independent_by_market"]["AST"]["graded"],0)
    after_tip={**archive,"quotes":[{**quote,"observed_at":"2026-11-08T21:01:00Z"}]}
    self.assertEqual(summarize(base,NOW,after_tip)["independent_by_market"]["AST"]["graded"],0)

 def test_latest_standard_only_not_most_favorable_winner(self):
    sources=[]
    for i,(captured,line) in enumerate([
          ("2026-11-08T20:01:00Z",4.5),
          ("2026-11-08T20:03:00Z",7.5)]):
        sources.append({**SOURCE["comparisons"][0],
                        "provider_projection_id":"std"+str(i),
                        "captured_at":captured,"line":line,
                        "source":"independent_prizepicksapi_com",
                        "more_tier":"standard","less_tier":"standard"})
    frozen=freeze({"records":[]},{**SOURCE,"comparisons":sources})
    report=summarize(settle(frozen,[GAME],NOW),NOW)
    # Actual=8. Last frozen line 7.5 produces a losing LESS lean.
    self.assertEqual(report["independent_by_market"]["AST"]["graded"],1)
    self.assertEqual(report["independent_by_market"]["AST"]["wins"],0)
    self.assertEqual(report["independent_by_market"]["AST"]["losses"],1)

 def test_no_fake_prices(self):
    saved=freeze({"records":[]},SOURCE)
    self.assertTrue(saved["records"][0]["not_sportsbook_odds"])
    self.assertFalse(summarize(saved,NOW)["verified_ev"])

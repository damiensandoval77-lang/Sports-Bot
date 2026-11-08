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
    self.assertEqual(summarize(result,NOW)["by_market"]["AST"]["wins"],1)
 def test_alternate_thresholds_not_counted_as_independent_hits(self):
    rows=[]
    for i,line in enumerate((3.5,5.5,7.5)):
        v={**SOURCE["comparisons"][0],
           "provider_projection_id":"different"+str(i),"line":line}
        rows.append(v)
    frozen=freeze({"records":[]},{**SOURCE,"comparisons":rows})
    graded=settle(frozen,[GAME],NOW)
    summary=summarize(graded,NOW)
    self.assertEqual(summary["settled"],3)
    self.assertEqual(summary["independent_player_market_count"],1)
    self.assertEqual(summary["independent_settled_center_lines"],1)
    self.assertEqual(summary["independent_by_market"]["AST"]["graded"],1)
    self.assertEqual(summary["independent_by_market"]["AST"]["wins"],1)
 def test_joint_v3_v2_shadows_are_frozen_and_graded(self):
    src={**SOURCE,"comparisons":[{
      **SOURCE["comparisons"][0],
      "minutes_v3_research":{
         "status":"PREGAME_MINUTES_V3_RESEARCH",
         "expected_minutes":31.5,"last_prior_date":"2026-11-07"},
      "minutes_v2_research_baseline":30,
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
 def test_no_fake_prices(self):
    saved=freeze({"records":[]},SOURCE)
    self.assertTrue(saved["records"][0]["not_sportsbook_odds"])
    self.assertFalse(summarize(saved,NOW)["verified_ev"])

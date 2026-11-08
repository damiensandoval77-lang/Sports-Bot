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
 def test_missing_final_does_not_invent_grades(self):
    saved=freeze({"records":[]},SOURCE)
    result=settle(saved,[],NOW)
    self.assertEqual(result["records"][0]["status"],"PENDING")
 def test_no_fake_prices(self):
    saved=freeze({"records":[]},SOURCE)
    self.assertTrue(saved["records"][0]["not_sportsbook_odds"])
    self.assertFalse(summarize(saved,NOW)["verified_ev"])

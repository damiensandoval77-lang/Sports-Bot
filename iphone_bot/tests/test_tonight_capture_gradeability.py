import datetime as dt
import unittest
from iphone_bot.tonight_capture_gradeability import reconcile

NOW=dt.datetime(2026,11,10,2,tzinfo=dt.timezone.utc)
SCHEDULE={"status":"THIRD_PARTY_NBA_SCHEDULE_ONLY","coverage_complete":True,
 "games":[{"game":"A @ B","date_eastern":"2026-11-09","start":"2026-11-10T00:00:00Z"},
          {"game":"C @ D","date_eastern":"2026-11-09","start":"2026-11-10T01:00:00Z"}]}
def quote(game="A @ B"):
 return {"source":"independent_prizepicksapi_com","is_demo":False,
  "game":game,"starts_at":"2026-11-10T00:00:00Z","player":"X","team":"A","stat":"PTS","line":15.5,"tier":"standard"}
def ai(game="A @ B"):
 return {"is_pregame_prediction":True,"line":None,"game":game,
   "start":"2026-11-10T00:00:00Z"}
def frozen(game="A @ B"):
 return {"game":game,"start":"2026-11-10T00:00:00Z","grade":"PENDING", "player":"X","team":"A","stat":"PTS","line":15.5}
def audit(q=None,a=None,f=None,actual=None,now=NOW):
 q=q if q is not None else [quote(),quote("C @ D")]
 a=a if a is not None else [ai(),ai("C @ D")]
 f=f if f is not None else [frozen(),frozen("C @ D")]
 return reconcile(SCHEDULE,{"status":"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE","count":len(q),"quotes":q},
   {"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE","predictions":a},
   {"status":"FROZEN_NEW_AI_ALL_MARKET","records":f},
   {"version":1,"records":actual or []},now=now)
class CaptureAuditTests(unittest.TestCase):
 def test_complete_capture_not_confused_with_zero_final_grades(self):
  out=audit()
  self.assertEqual(out["status"],"CAPTURE_VERIFIED")
  self.assertEqual(out["summary"]["schedule_games"],2)
  self.assertEqual(out["summary"]["total_line_backed_graded"],0)
 def test_standard_market_missing_even_with_other_frozen_market(self):
  second={**quote(),"player":"Y","tier":"standard"}
  out=audit(q=[quote(),second,quote("C @ D")])
  self.assertEqual(out["status"],"CAPTURE_INCOMPLETE")
  self.assertIn("A @ B: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL",out["issues"])
  self.assertEqual(out["games"][0]["standard_markets_without_frozen_model"],1)
  self.assertEqual(out["games"][0]["standard_price_moves_from_original_frozen_line"],0)
  self.assertEqual(out["games"][0]["standard_player_stat_markets_never_primary_frozen"],1)
 def test_different_saved_standard_threshold_is_missing_not_covered(self):
  moved={**quote(),"line":16.5}
  out=audit(q=[quote(),moved,quote("C @ D")])
  self.assertEqual(out["status"],"CAPTURE_INCOMPLETE")
  self.assertIn("A @ B: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL",out["issues"])
  self.assertEqual(out["games"][0]["standard_markets_without_frozen_model"],1)
  self.assertEqual(out["games"][0]["standard_price_moves_from_original_frozen_line"],1)
  self.assertEqual(out["games"][0]["standard_player_stat_markets_never_primary_frozen"],0)
 def test_goblin_demon_quoted_lines_do_not_count_as_unfrozen_standard_markets(self):
  alternative={**quote(),"player":"Y","tier":"demon"}
  out=audit(q=[quote(),alternative,quote("C @ D")])
  self.assertEqual(out["status"],"CAPTURE_VERIFIED")
  self.assertEqual(out["summary"]["total_standard_source_quotes"],2)
 def test_one_game_missing_line_backed_fails_even_with_quotes(self):
  out=audit(f=[frozen()])
  self.assertEqual(out["status"],"CAPTURE_INCOMPLETE")
  self.assertIn("C @ D: PROVIDER_QUOTES_WITH_NO_FROZEN_LINE_BACKED_MODEL",out["issues"])
 def test_one_graded_market_does_not_hide_other_overdue_markets(self):
  first={**frozen(),"grade":"GRADED"}
  second=frozen()
  out=audit(f=[first,second,frozen("C @ D")],
            now=dt.datetime(2026,11,10,11,tzinfo=dt.timezone.utc))
  self.assertEqual(out["status"],"CAPTURE_INCOMPLETE")
  self.assertIn("A @ B: LINE_BACKED_GRADING_OVERDUE_CHECK_FINAL_FEED",out["issues"])
  self.assertEqual(out["games"][0]["line_backed_graded"],1)
  self.assertEqual(out["games"][0]["line_backed_pending"],1)
 def test_pending_games_before_grace_period_are_not_called_overdue(self):
  out=audit()
  self.assertNotIn("A @ B: LINE_BACKED_GRADING_OVERDUE_CHECK_FINAL_FEED",out["issues"])
 def test_missing_source_data_cannot_pass(self):
  out=audit(q=[quote()])
  self.assertIn("C @ D: NO_CAPTURED_PROVIDER_LINES",out["issues"])
 def test_missing_ai_cannot_pass(self):
  out=audit(a=[ai()])
  self.assertIn("C @ D: NO_SAVED_PREGAME_AI",out["issues"])
 def test_research_fallback_counts_separately_and_never_grades_model(self):
  original=quote()
  moved={**quote(),"line":16.5}
  archive={"status":"IMMUTABLE_PRETIP_STANDARD_QUOTE_AI_RESEARCH",
           "records":[{**moved,"research_only":True,"calibrated":False,
                       "grade":"UNSETTLED_RESEARCH","more_tier":"standard","less_tier":"standard"}]}
  base=audit(q=[original,moved,quote("C @ D")])
  self.assertEqual(base["summary"]["total_standard_markets_without_frozen_model"],1)
  report=reconcile(SCHEDULE,
    {"status":"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE","count":3,"quotes":[original,moved,quote("C @ D")]},
    {"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE","predictions":[ai(),ai("C @ D")]},
    {"status":"FROZEN_NEW_AI_ALL_MARKET","records":[frozen(),frozen("C @ D")]},
    {"records":[]},now=NOW,research=archive)
  self.assertEqual(report["summary"]["total_missing_primary_with_separate_research_receipt"],1)
  self.assertEqual(report["summary"]["total_missing_primary_without_any_ai_receipt"],0)
  self.assertEqual(report["summary"]["total_standard_markets_without_frozen_model"],1)
  self.assertEqual(report["status"],"CAPTURE_INCOMPLETE")
  self.assertEqual(report["summary"]["total_line_backed_graded"],0)

 def test_actual_grading_requires_prior_prediction_identity(self):
  grades=[{"game":"A @ B","start":"2026-11-10T00:00:00Z","status":"GRADED"}]
  out=audit(actual=grades)
  self.assertEqual(out["summary"]["total_ai_only_graded"],1)
  self.assertEqual(out["summary"]["total_line_backed_graded"],0)
if __name__=="__main__":unittest.main()

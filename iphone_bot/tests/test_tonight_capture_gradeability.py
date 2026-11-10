import datetime as dt
import unittest
from iphone_bot.tonight_capture_gradeability import reconcile

NOW=dt.datetime(2026,11,10,2,tzinfo=dt.timezone.utc)
SCHEDULE={"status":"THIRD_PARTY_NBA_SCHEDULE_ONLY","coverage_complete":True,
 "games":[{"game":"A @ B","date_eastern":"2026-11-09","start":"2026-11-10T00:00:00Z"},
          {"game":"C @ D","date_eastern":"2026-11-09","start":"2026-11-10T01:00:00Z"}]}
def quote(game="A @ B"):
 return {"source":"independent_prizepicksapi_com","is_demo":False,
  "game":game,"starts_at":"2026-11-10T00:00:00Z","player":"X","team":"A","stat":"PTS"}
def ai(game="A @ B"):
 return {"is_pregame_prediction":True,"line":None,"game":game,
   "start":"2026-11-10T00:00:00Z"}
def frozen(game="A @ B"):
 return {"game":game,"start":"2026-11-10T00:00:00Z","grade":"PENDING"}
def audit(q=None,a=None,f=None,actual=None):
 q=q if q is not None else [quote(),quote("C @ D")]
 a=a if a is not None else [ai(),ai("C @ D")]
 f=f if f is not None else [frozen(),frozen("C @ D")]
 return reconcile(SCHEDULE,{"status":"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE","count":len(q),"quotes":q},
   {"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE","predictions":a},
   {"status":"FROZEN_NEW_AI_ALL_MARKET","records":f},
   {"version":1,"records":actual or []},now=NOW)
class CaptureAuditTests(unittest.TestCase):
 def test_complete_capture_not_confused_with_zero_final_grades(self):
  out=audit()
  self.assertEqual(out["status"],"CAPTURE_VERIFIED")
  self.assertEqual(out["summary"]["schedule_games"],2)
  self.assertEqual(out["summary"]["total_line_backed_graded"],0)
 def test_one_game_missing_line_backed_fails_even_with_quotes(self):
  out=audit(f=[frozen()])
  self.assertEqual(out["status"],"CAPTURE_INCOMPLETE")
  self.assertIn("C @ D: PROVIDER_QUOTES_WITH_NO_FROZEN_LINE_BACKED_MODEL",out["issues"])
 def test_missing_source_data_cannot_pass(self):
  out=audit(q=[quote()])
  self.assertIn("C @ D: NO_CAPTURED_PROVIDER_LINES",out["issues"])
 def test_missing_ai_cannot_pass(self):
  out=audit(a=[ai()])
  self.assertIn("C @ D: NO_SAVED_PREGAME_AI",out["issues"])
 def test_actual_grading_requires_prior_prediction_identity(self):
  grades=[{"game":"A @ B","start":"2026-11-10T00:00:00Z","status":"GRADED"}]
  out=audit(actual=grades)
  self.assertEqual(out["summary"]["total_ai_only_graded"],1)
  self.assertEqual(out["summary"]["total_line_backed_graded"],0)
if __name__=="__main__":unittest.main()

import datetime as dt
import unittest
from iphone_bot.published_pick_settlement import evaluate

NOW=dt.datetime(2026,11,11,8,tzinfo=dt.timezone.utc)
BASE={"player_id":"123","team":"BOS","game":"Boston Celtics @ Philadelphia 76ers",
      "start":"2026-11-11T01:00:00Z","stat":"PTS","line":25.5,
      "captured_at":"2026-11-10T23:05:00Z","market_updated":"2026-11-10T23:00:00Z",
      "research_only":True,"pickem_tier":"standard","standard_line_two_sided_verified":True,
      "grade":"PENDING","actual":None}
def ledger(*rows):return {"status":"FROZEN_NEW_AI_ALL_MARKET","records":list(rows)}
def finals(*rows):return {"records":list(rows)}
def fin(status="GRADED"):
 return {"player_id":"123","team":"BOS","game":BASE["game"],"start":BASE["start"],
         "stat":"PTS","source_game_id":"0022600123","status":status,
         "final_source":"NBA_CDN_FINAL" if status=="GRADED" else "NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
         "actual":23 if status=="GRADED" else None,
         "verified_dnp_reason":"INACTIVE" if status!="GRADED" else None}
class PublishedCaptureSettlementTests(unittest.TestCase):
 def test_cross_provider_dnp_ids_match_only_exact_verified_event(self):
  p={**BASE,"grade":"EXCLUDED_VERIFIED_DNP","source_game_id":"401909960",
     "final_source":"ESPN_FINAL_BOX_ABSENT_INJURY_LISTED",
     "verified_dnp_reason":"Final box inactive","actual":None,"direction_hit":None}
  final=fin("EXCLUDED_VERIFIED_DNP")
  self.assertEqual(evaluate(ledger(p),finals(final),NOW)["status"],"READY")
  from iphone_bot.published_pick_settlement import same_verified_event
  self.assertFalse(same_verified_event(p,{**final,"start":"2026-11-12T01:00:00Z"}))
  self.assertFalse(same_verified_event(p,{**final,"team":"NYK"}))
  self.assertFalse(same_verified_event(p,{**final,"player_id":"456"}))
  self.assertFalse(same_verified_event(p,{**final,"source_game_id":"401909961","final_source":"ESPN_FINAL"}))
  self.assertFalse(same_verified_event(p,{**final,"source_game_id":"wrong"}))

 def test_verified_pregame_pending_is_allowed_before_official_final(self):
  r=evaluate(ledger(BASE),finals(),NOW.replace(hour=2))
  self.assertEqual(r["status"],"READY")
  self.assertEqual(r["counts"]["pending"],1)
 def test_official_final_requires_immediate_settlement(self):
  r=evaluate(ledger(BASE),finals(fin()),NOW)
  self.assertEqual(r["issues"]["VERIFIED_FINAL_NOT_APPLIED"],1)
  self.assertEqual(r["actionable_verified_finals"],1)
 def test_official_dnp_requires_void_not_pending(self):
  r=evaluate(ledger(BASE),finals(fin("EXCLUDED_VERIFIED_DNP")),NOW)
  self.assertEqual(r["actionable_verified_finals"],1)
  self.assertEqual(r["status"],"DEGRADED")
 def test_verified_void_counts_neither_win_loss_nor_pending(self):
  p={**BASE,"grade":"EXCLUDED_VERIFIED_DNP","source_game_id":"0022600123",
     "final_source":"NBA_OFFICIAL_INACTIVE_CROSSCHECKED","verified_dnp_reason":"INACTIVE",
     "actual":None,"direction_hit":None}
  r=evaluate(ledger(p),finals(fin("EXCLUDED_VERIFIED_DNP")),NOW)
  self.assertEqual(r["status"],"READY")
  self.assertEqual(r["counts"].get("pending",0),0)
  self.assertEqual(r["counts"]["verified_dnp_excluded"],1)
 def test_overdue_without_real_final_fails_not_infers_result(self):
  r=evaluate(ledger(BASE),finals(),NOW+dt.timedelta(hours=4))
  self.assertEqual(r["overdue_missing_verified_finals"],1)
  self.assertEqual(r["status"],"DEGRADED")
 def test_genuine_graded_pick_passes(self):
  p={**BASE,"grade":"GRADED","source_game_id":"0022600123",
    "final_source":"NBA_CDN_FINAL","actual":23,"absolute_error":2.5,
    "direction_hit":False}
  r=evaluate(ledger(p),finals(fin()),NOW)
  self.assertEqual(r["status"],"READY")
  self.assertEqual(r["counts"]["graded"],1)
 def test_grade_must_match_independent_final_value(self):
  p={**BASE,"grade":"GRADED","source_game_id":"0022600123",
     "final_source":"NBA_CDN_FINAL","actual":29,"absolute_error":3.5,
     "direction_hit":True}
  r=evaluate(ledger(p),finals(fin()),NOW)
  self.assertIn("GRADED_FINAL_MISMATCH",r["issues"])
  self.assertFalse(r["reconciled"])
 def test_completed_flag_does_not_confuse_pending_with_success(self):
  r=evaluate(ledger(BASE),finals(),NOW.replace(hour=2))
  self.assertTrue(r["reconciled"])
  self.assertFalse(r["complete"])
 def test_standard_direction_is_checked_against_original_line(self):
  p={**BASE,"grade":"GRADED","source_game_id":"0022600123",
     "final_source":"NBA_CDN_FINAL","actual":23,"absolute_error":2.5,
     "direction_hit":True,"estimated_hit_chance":{"modeled_direction":"More"}}
  r=evaluate(ledger(p),finals(fin()),NOW)
  self.assertIn("INCORRECT_STANDARD_LINE_DIRECTION_GRADE",r["issues"])
 def test_exact_line_push_requires_no_win_or_loss(self):
  p={**BASE,"line":23,"grade":"GRADED","source_game_id":"0022600123",
     "final_source":"NBA_CDN_FINAL","actual":23,"absolute_error":2.5,
     "direction_hit":None,"estimated_hit_chance":{"modeled_direction":"More"}}
  r=evaluate(ledger(p),finals(fin()),NOW)
  self.assertTrue(r["reconciled"])
  p["direction_hit"]=False
  r=evaluate(ledger(p),finals(fin()),NOW)
  self.assertIn("PUSH_RECORDED_AS_WIN_OR_LOSS",r["issues"])
 def test_reject_duplicate_saved_pick_versions(self):
  r=evaluate(ledger(BASE,BASE),finals(),NOW.replace(hour=2))
  self.assertIn("INVALID_OR_DUPLICATE_FROZEN_PICK",r["issues"])
 def test_different_lines_are_separate_gradeable_records(self):
  a={**BASE,"line":25.5}
  b={**BASE,"line":26.5}
  r=evaluate(ledger(a,b),finals(),NOW.replace(hour=2))
  self.assertEqual(r["status"],"READY")
  self.assertEqual(r["counts"]["frozen_picks"],2)
 def test_alternate_and_post_tip_capture_fail_closed(self):
  r=evaluate(ledger({**BASE,"pickem_tier":"demon"},
                    {**BASE,"line":26.5,"captured_at":"2026-11-11T02:00:00Z"}),
             finals(),NOW)
  self.assertEqual(r["issues"]["INVALID_OR_DUPLICATE_FROZEN_PICK"],2)
if __name__=="__main__":unittest.main()

import unittest
from iphone_bot.minutes_opportunity_joint_grade import grade
def rec(date="2026-11-08T23:30:00Z",last="2026-11-07",market="AST"):
 return {"market":market,"status":"SETTLED","event_start":date,
 "captured_at":"2026-11-08T17:00:00Z","player_id":"123",
 "player":"Example Player","team":"BOS","game":"Boston Celtics @ Miami Heat",
 "bookmaker":"BookA","line":5.5,"actual":8.0,"actual_minutes":33.0,
 "original_projection":6.0,"opponent_shadow_projection":6.2,
 "combined_projection":6.1,"frozen_minutes_v2_research":{"expected_minutes":30.},
 "minutes_v3_research":{"status":"PREGAME_MINUTES_V3_RESEARCH",
    "expected_minutes":32.,"last_prior_date":last},
 "opportunity_v2_research":{"markets":{market:{
    "status":"PREGAME_OPPORTUNITY_V2_RESEARCH",
    "projection":7.,"last_prior_game":last,
    "source_kind":"BOX_SCORE_RATE_PROXY"}}}}
class JointProspectiveGradeTests(unittest.TestCase):
 def test_both_frozen_models_grade_identically_matched_result(self):
  result=grade([rec()])
  self.assertEqual(result["markets"]["AST"]["paired"],1)
  self.assertEqual(result["markets"]["MIN"]["paired"],1)
  self.assertEqual(result["markets"]["AST"]["wins"],1)
  self.assertEqual(result["markets"]["AST"]["baseline_wins"],1)
  self.assertFalse(result["production_applied"])
 def test_missing_frozen_shadow_is_never_retrospectively_filled(self):
  item=rec();item.pop("opportunity_v2_research")
  self.assertEqual(grade([item])["markets"]["AST"]["paired"],0)
 def test_same_local_game_date_is_rejected_even_if_utc_date_is_next(self):
  item=rec(date="2026-11-09T01:00:00Z",last="2026-11-08")
  self.assertEqual(grade([item])["markets"]["AST"]["paired"],0)
  self.assertEqual(grade([item])["missing"]["UNSAFE_FEATURE_DATE"],1)
 def test_multiple_bookmaker_quotes_are_not_independent(self):
  a=rec();b=dict(a,bookmaker="BookB",line=6.5)
  self.assertEqual(grade([a,b])["markets"]["AST"]["paired"],1)

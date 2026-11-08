import unittest
from iphone_bot.shooting_efficiency_grade import grade
class ShootingProspectiveGradeTests(unittest.TestCase):
 def test_no_retrograde_when_shadow_missing(self):
    r=grade([{"market":"PTS","status":"SETTLED","event_start":"2026-11-07T19:00:00Z",
         "player_id":"1","team":"BOS","bookmaker":"Book",
         "line":20.5,"actual":22,"combined_projection":23,"game":"BOS @ NYK",
         "captured_at":"2026-11-07T16:00:00Z"}])
    self.assertEqual(r["independent_frozen_pts_markets"],0)
    self.assertFalse(r["verified_edge"])
 def test_frozen_projection_not_rebuilt(self):
    record={"market":"PTS","status":"SETTLED","event_start":"2026-11-07T19:00:00Z",
         "player_id":"1","team":"BOS","bookmaker":"Book",
         "line":20.5,"actual":22,"combined_projection":19,"original_projection":18,"opponent_shadow_projection":20,"game":"BOS @ NYK",
         "captured_at":"2026-11-07T16:00:00Z",
         "shooting_efficiency_v1":{"status":"PREGAME_SHOOTING_SHADOW_RESEARCH",
             "blended_projection":21,"projection":25,
             "last_prior_game":"2026-11-06","opponent_adjustment_applied":False}}
    r=grade([record])
    self.assertEqual(r["independent_frozen_pts_markets"],1)
    self.assertEqual(r["combined_ai"]["directional_wins"],0)
    self.assertEqual(r["shooting_v1_blend"]["directional_wins"],1)
    self.assertEqual(r["shooting_v1_raw"]["directional_wins"],1)
 def test_no_future_game_feature(self):
    record={"market":"PTS","status":"SETTLED","event_start":"2026-11-07T19:00:00Z",
         "player_id":"1","team":"BOS","bookmaker":"Book",
         "line":20.5,"actual":22,"combined_projection":19,"original_projection":18,"opponent_shadow_projection":20,"game":"BOS @ NYK",
         "captured_at":"2026-11-07T16:00:00Z",
         "shooting_efficiency_v1":{"status":"PREGAME_SHOOTING_SHADOW_RESEARCH",
             "blended_projection":21,"projection":25,"last_prior_game":"2026-11-07"}}
    r=grade([record])
    self.assertEqual(r["independent_frozen_pts_markets"],0)
    self.assertEqual(r["skipped"]["NON_PRETIP_FEATURE_DATE"],1)

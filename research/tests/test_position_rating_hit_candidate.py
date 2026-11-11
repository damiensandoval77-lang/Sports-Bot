import copy
import unittest
from research.position_rating_hit_candidate import estimate,POSITIONS

CAP="2026-11-10T19:00:00Z"
TIP="2026-11-11T01:00:00Z"
OLD="2026-11-09T12:00:00Z"

def inputs():
    return {"position":"PG","stat":"AST","opponent":"BOS",
    "baseline_projection":7.1,"standard_line":6.5,"side":"MORE",
    "captured_at":CAP,"tipoff":TIP,"model_id":"candidate-one",
    "position_allowed":{"position":"PG","stat":"AST","opponent":"BOS",
         "allowed_per_listed_player":4.4,"league_position_baseline":4,
         "sample_games":8,"source":"complete position game source","observed_at":OLD},
    "team_def_rating":{"opponent":"BOS","metric":"POINTS_ALLOWED_PER_100_POSSESSIONS",
         "rating":110,"league_baseline":114,"source":"verified possession-adjusted rating","observed_at":OLD},
    "expected_minutes":{"matchup":33,"baseline":32,
         "source":"pregame minutes model","observed_at":OLD},
    "validation_errors":[{"error":(i%9-4)*.7,"source":"heldout error","observed_at":OLD}
                         for i in range(90)]}

class PositionRatingTests(unittest.TestCase):
    def test_all_five_listed_positions_can_be_modeled(self):
        for position in POSITIONS:
            x=inputs();x["position"]=position;x["position_allowed"]["position"]=position
            r=estimate(**x)
            self.assertEqual(r["position"],position)
            self.assertFalse(r["production_approved"])
            self.assertFalse(r["calibrated"])
            self.assertGreaterEqual(r["modeled_selected_probability"],0)

    def test_opponent_allowance_affects_estimate_not_historical_hit_frequency(self):
        x=inputs();a=estimate(**x)
        x["position_allowed"]["allowed_per_listed_player"]=6.6
        b=estimate(**x)
        self.assertGreater(b["matchup_projection"],a["matchup_projection"])

    def test_no_fake_rating_or_unknown_positional_match(self):
        x=inputs();x["team_def_rating"]["metric"]="TEAM_PPG_ALLOWED"
        with self.assertRaises(ValueError):estimate(**x)
        x=inputs();x["position_allowed"]["position"]="C"
        with self.assertRaises(ValueError):estimate(**x)

    def test_future_factors_rejected(self):
        for key in ("position_allowed","team_def_rating","expected_minutes"):
            x=inputs();x[key]["observed_at"]=TIP
            with self.assertRaises(ValueError):estimate(**x)

    def test_posttip_capture_rejected(self):
        x=inputs();x["captured_at"]=TIP
        with self.assertRaises(ValueError):estimate(**x)

    def test_insufficient_games_or_missing_errors_rejected(self):
        x=inputs();x["position_allowed"]["sample_games"]=2
        with self.assertRaises(ValueError):estimate(**x)
        x=inputs();x["validation_errors"]=[]
        with self.assertRaises(ValueError):estimate(**x)

    def test_defense_rating_variation_changes_projection_but_remains_unverified(self):
        x=inputs();base=estimate(**x)
        x["team_def_rating"]["rating"]=125
        changed=estimate(**x)
        self.assertGreater(changed["matchup_projection"],base["matchup_projection"])
        self.assertTrue(changed["research_only"])

    def test_standard_line_side_frozen(self):
        x=inputs();a=estimate(**x)
        x["side"]="LESS";b=estimate(**x)
        self.assertEqual(a["original_line"],b["original_line"])
        self.assertEqual(a["matchup_projection"],b["matchup_projection"])

if __name__=="__main__":unittest.main()

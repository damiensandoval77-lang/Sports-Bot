"""Research-only feature provenance and leakage regression tests."""
import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "matchup_hit_estimate.py"
spec = importlib.util.spec_from_file_location("matchup_hit_estimate", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

TIP = "2026-11-12T00:00:00Z"
LOCK = "2026-11-11T20:00:00Z"
OLD = "2026-11-10T00:00:00Z"


def inputs():
    return dict(
        projection=10, line=10.5, side="OVER", tipoff=TIP, captured_at=LOCK,
        stat="AST", model_id="research-prototype",
        factors={k: dict(baseline=10, matchup=10, source="pregame source", observed_at=OLD)
                 for k in module.REQUIRED},
        residuals=[dict(error=i % 7 - 3, source="held-out error", observed_at=OLD)
                   for i in range(70)],
    )


class MatchupResearchTests(unittest.TestCase):
    def test_opponent_scenario_changes_probability_not_historical_hit_count(self):
        arg = inputs()
        original = module.estimate(**arg)
        arg["factors"]["opponent_position_defense"]["matchup"] = 12
        new = module.estimate(**arg)
        self.assertGreater(new["matchup_projection"], original["matchup_projection"])
        self.assertGreater(new["modeled_selected_probability"], original["modeled_selected_probability"])
        self.assertFalse(new["calibrated"])
        self.assertTrue(new["research_only"])

    def test_missing_feature_fails_closed(self):
        arg = inputs()
        del arg["factors"]["depth_role"]
        with self.assertRaises(ValueError):
            module.estimate(**arg)

    def test_future_features_fail_closed(self):
        arg = inputs()
        arg["factors"]["pace_possessions"]["observed_at"] = TIP
        with self.assertRaises(ValueError):
            module.estimate(**arg)

    def test_future_residual_fails_closed(self):
        arg = inputs()
        arg["residuals"][0]["observed_at"] = TIP
        with self.assertRaises(ValueError):
            module.estimate(**arg)

    def test_posttip_capture_fails_closed(self):
        arg = inputs()
        arg["captured_at"] = TIP
        with self.assertRaises(ValueError):
            module.estimate(**arg)

    def test_missing_validation_sample_fails_closed(self):
        arg = inputs()
        arg["residuals"] = arg["residuals"][:10]
        with self.assertRaises(ValueError):
            module.estimate(**arg)

    def test_raw_historical_hit_rate_is_never_used(self):
        arg = inputs()
        self.assertNotIn("historical_hit_rate", arg)
        self.assertIn("modeled_selected_probability", module.estimate(**arg))


if __name__ == "__main__":
    unittest.main()

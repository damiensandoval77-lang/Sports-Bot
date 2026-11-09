import datetime as dt
import unittest
from iphone_bot.reliability_guardrails import validate

NOW = dt.datetime(2026, 11, 9, 23, 0, tzinfo=dt.timezone.utc)

def base():
    return {
        "generated_at": "2026-11-09T22:50:00Z",
        "expected_game_ids": ["1", "2"],
        "games": [{"id": "1", "status": "scheduled"}, {"id": "2", "status": "live"}],
        "cards": [{"id": "c1", "line": 21.5, "projection": 24, "lean": "OVER", "probability": .61},
                  {"id": "c2", "line": 18.5, "projection": None, "lean": None, "probability": None}]
    }

class GuardrailTests(unittest.TestCase):
    def test_healthy_snapshot(self):
        self.assertEqual(validate(base(), now=NOW)[0], [])
    def test_missing_schedule_game(self):
        s = base()
        s["games"].pop()
        self.assertIn("missing scheduled games", " ".join(validate(s, now=NOW)[0]))
    def test_stale_snapshot(self):
        s = base()
        s["generated_at"] = "2026-11-09T20:00:00Z"
        self.assertIn("snapshot stale", " ".join(validate(s, now=NOW)[0]))
    def test_no_fake_lean(self):
        s = base()
        s["cards"][1]["lean"] = "OVER"
        self.assertIn("invented lean", " ".join(validate(s, now=NOW)[0]))
    def test_no_fake_probability(self):
        s = base()
        s["cards"][1]["probability"] = .8
        self.assertIn("invented lean/probability", " ".join(validate(s, now=NOW)[0]))
    def test_graded_final_deadline(self):
        s = base()
        s["games"][1] = {"id": "2", "status": "final", "final_at": "2026-11-09T15:00:00Z", "ungraded_predictions": 4}
        self.assertIn("ungraded", " ".join(validate(s, now=NOW)[0]))
    def test_grade_grace_period(self):
        s = base()
        s["games"][1] = {"id": "2", "status": "final", "final_at": "2026-11-09T22:00:00Z", "ungraded_predictions": 4}
        self.assertEqual(validate(s, now=NOW)[0], [])
    def test_missing_schedule_is_not_success(self):
        s = base()
        s["expected_game_ids"] = []
        self.assertIn("schedule is empty", " ".join(validate(s, now=NOW)[0]))
    def test_invalid_probability(self):
        s = base()
        s["cards"][0]["probability"] = 75
        self.assertIn("invalid probability", " ".join(validate(s, now=NOW)[0]))

if __name__ == "__main__":
    unittest.main()

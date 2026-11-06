"""Regression tests for paired, pregame-locked model evaluation."""
import unittest
from iphone_bot.model_performance import paired_model_comparison, compute_performance


def settled(player, actual, original, shadow, combined, *, book="FanDuel"):
    return {
        "status": "SETTLED", "player_id": str(player),
        "event_start": "2026-11-06T23:00:00+00:00",
        "captured_at": "2026-11-06T20:00:00+00:00",
        "market": "PTS", "line": 15.5, "actual": actual,
        "original_projection": original,
        "opponent_shadow_projection": shadow,
        "combined_projection": combined, "bookmaker": book,
        "american_odds": -110, "side": "OVER", "over_odds": -110,
        "under_odds": -110,
    }


class PairedComparisonTest(unittest.TestCase):
    def test_identical_player_market_not_double_counted(self):
        a = settled(101, 20, 17, 19, 18)
        b = dict(a, bookmaker="DraftKings", captured_at="2026-11-06T20:10:00+00:00")
        result = paired_model_comparison([a, b])
        self.assertEqual(result["overall"]["sample_size"], 1)
        self.assertEqual(result["overall"]["mae"]["original"], 3)
        self.assertEqual(result["overall"]["mae"]["opponent_aware"], 1)
        self.assertEqual(result["overall"]["mae"]["combined"], 2)
        self.assertEqual(result["overall"]["combined_mae_change_vs_original"], -1)
        self.assertFalse(result["overall"]["sufficient_sample"])

    def test_missing_shadow_excluded_from_fair_comparison(self):
        a = settled(101, 20, 17, 19, 18)
        b = settled(102, 16, 14, None, 14)
        result = compute_performance([a, b])
        self.assertEqual(result["models"]["original"]["observations"], 2)
        self.assertEqual(result["paired_comparison"]["overall"]["sample_size"], 1)

    def test_direction_counts_and_pregame_requirement(self):
        good = settled(101, 10, 20, 13, 16.5)
        late = dict(settled(102, 10, 20, 13, 16.5),
                    captured_at="2026-11-07T00:00:00+00:00")
        result = paired_model_comparison([good, late])["overall"]
        self.assertEqual(result["sample_size"], 1)
        self.assertEqual(result["direction"]["original"]["losses"], 1)
        self.assertEqual(result["direction"]["opponent_aware"]["wins"], 1)


if __name__ == "__main__":
    unittest.main()

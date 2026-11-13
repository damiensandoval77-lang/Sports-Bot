"""End-to-end offline acceptance tests: frozen pregame -> verified final -> immutable merge.

Synthetic fixtures exercise the production pipeline without claiming a new real game
was graded or consuming external provider credits.
"""
import unittest

from iphone_bot.paper_pick_pipeline import snapshot, settle, identity
from iphone_bot.settlement_merge import merge

START = "2026-11-10T00:00:00+00:00"
CAPTURE = "2026-11-09T20:00:00+00:00"
AFTER = "2026-11-10T04:00:00+00:00"


def pregame():
    return {
        "start": START,
        "game": "Boston Celtics @ Charlotte Hornets",
        "player": "Example Player",
        "player_id": "p123",
        "team": "BOS",
        "stat": "PTS",
        "projection": 24.5,
        "combined_projection": 24.5,
        "book_quotes": [{
            "name": "FixtureBook",
            "line": 20.5,
            "over": -110,
            "under": -110,
        }],
    }


def verified_final(points=25, confirmed=True):
    return {
        "source": "ESPN_FINAL",
        "final_confirmed": confirmed,
        "player": "Example Player",
        "date": "2026-11-09",  # Date in America/New_York
        "team": "BOS",
        "opponent": "CHA",
        "source_game_id": "fixture-001",
        "PTS": points,
        "REB": 4,
        "AST": 3,
        "PRA": points + 7,
        "MIN": 31,
    }


class FinalGradeAcceptance(unittest.TestCase):
    def test_frozen_pregame_final_grade_and_idempotent_merge(self):
        original = snapshot([pregame()], CAPTURE)
        self.assertEqual(len(original), 1)
        self.assertEqual(original[0]["status"], "PENDING")
        self.assertEqual(original[0]["side"], "OVER")
        frozen = {k: original[0][k] for k in (
            "captured_at", "event_start", "line", "bookmaker",
            "original_projection", "combined_projection", "side")}
        graded = settle(original, [verified_final()], now=AFTER)
        self.assertEqual(graded[0]["status"], "SETTLED")
        self.assertEqual(graded[0]["actual"], 25)
        self.assertEqual(graded[0]["result"], "WIN")
        self.assertEqual(graded[0]["settlement_source"], "ESPN_FINAL")
        result = merge(original, graded)
        self.assertEqual(result[0]["status"], "SETTLED")
        self.assertEqual({k: result[0][k] for k in frozen}, frozen)
        self.assertEqual(merge(result, graded), result)
        self.assertEqual(len({identity(r) for r in result}), 1)

    def test_unverified_final_never_grades(self):
        original = snapshot([pregame()], CAPTURE)
        result = settle(original, [verified_final(40, confirmed=False)], now=AFTER)
        self.assertEqual(result[0]["status"], "PENDING")
        self.assertNotIn("actual", result[0])

    def test_conflicting_final_sources_do_not_grant_a_win(self):
        original = snapshot([pregame()], CAPTURE)
        evidence = [verified_final(25), {**verified_final(18),
                                         "source": "NBA_CDN_FINAL"}]
        result = settle(original, evidence, now=AFTER)
        self.assertEqual(result[0]["status"], "PENDING")

    def test_no_pretip_snapshot_after_tipoff(self):
        result = snapshot([pregame()], "2026-11-10T00:01:00+00:00")
        self.assertEqual(result, [])

    def test_repeated_capture_keeps_original_market(self):
        first = snapshot([pregame()], CAPTURE)
        altered = pregame()
        altered["combined_projection"] = 10.0
        altered["book_quotes"][0]["line"] = 20.5
        later = snapshot([altered], "2026-11-09T22:00:00+00:00",
                         existing=first)
        self.assertEqual(len(later), 1)
        self.assertEqual(later[0]["side"], "OVER")
        self.assertEqual(later[0]["captured_at"], first[0]["captured_at"])


if __name__ == "__main__":
    unittest.main()

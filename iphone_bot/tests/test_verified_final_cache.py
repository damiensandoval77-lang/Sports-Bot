import tempfile
import unittest
from pathlib import Path
from iphone_bot.verified_final_cache import verified_row, merge_rows, read_cache, write_cache

def row():
    return {
        "player": "Test Player", "team": "MIA", "opponent": "SAC",
        "date": "2026-11-08", "source": "NBA_CDN_FINAL",
        "source_game_id": "0022600200", "final_confirmed": True,
        "PTS": 14, "REB": 5, "AST": 3, "PRA": 22, "MIN": 24,
    }

class FinalCacheTests(unittest.TestCase):
    def test_valid_verified_final_persists_for_outage(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "cache.json"
            self.assertEqual(write_cache(p, [], [row()]), [row()])
            self.assertEqual(read_cache(p), [row()])
            # Second run with zero source responses retains verified rows.
            self.assertEqual(write_cache(p, read_cache(p), []), [row()])

    def test_invalid_or_nonfinal_data_never_cached(self):
        self.assertFalse(verified_row({**row(), "final_confirmed": False}))
        self.assertFalse(verified_row({**row(), "MIN": 0}))
        self.assertFalse(verified_row({**row(), "PRA": 999}))
        self.assertFalse(verified_row({**row(), "source": "UNVERIFIED"}))
        self.assertEqual(merge_rows([], [{**row(), "final_confirmed": False}]), [])

    def test_conflicting_actuals_do_not_get_silently_graded(self):
        self.assertEqual(merge_rows([row()], [{**row(), "PTS": 15, "PRA": 23}]), [])

    def test_unverified_absence_is_not_dnp(self):
        self.assertFalse(verified_row({**row(), "dnp_final_verified": True, "dnp_reason": None}))

if __name__ == "__main__":
    unittest.main()

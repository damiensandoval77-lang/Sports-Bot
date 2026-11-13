import unittest
from scripts.mobile_board_health import board_rendered

class MobileBoardHealth(unittest.TestCase):
    def test_pregame_saved_picks_require_rendered_cards(self):
        self.assertFalse(board_rendered(0, 904))
    def test_actual_empty_slate_is_allowed(self):
        self.assertTrue(board_rendered(0, 0))
    def test_rendered_board_is_allowed(self):
        self.assertTrue(board_rendered(1, 904))

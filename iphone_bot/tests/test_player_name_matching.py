"""Guard sportsbook to current-season NBA roster matching across diacritics."""
import unittest
from iphone_bot.compare_live_models import key

class PlayerIdentityTests(unittest.TestCase):
    def test_luka_unicode_matches_odds_provider(self):
        self.assertEqual(key("Luka Doncic"),key("Luka Dončić"))
        self.assertEqual(key("Nikola Jokić"),key("Nikola Jokic"))
        self.assertEqual(key("Bogdan Bogdanović"),key("Bogdan Bogdanovic"))
    def test_only_exact_full_names_match(self):
        self.assertNotEqual(key("Luka Doncic"),key("Luka Garza"))
        self.assertNotEqual(key("Luka Doncic"),key("Doncic"))
        self.assertNotEqual(key("Luka Doncic"),key("Luka Doncic Jr"))
    def test_punctuation_and_spaces_do_not_change_identity(self):
        self.assertEqual(key("P.J. Washington"),key("PJ Washington"))
        self.assertEqual(key("D'Angelo Russell"),key("DAngelo Russell"))

if __name__=="__main__":unittest.main()

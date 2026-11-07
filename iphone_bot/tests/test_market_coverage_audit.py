import unittest
from iphone_bot.market_coverage_audit import audit

def odds():
    return {"updated_at":"2026-11-06T20:00:00Z","picks":[
        {"player":"Luka Doncic","game":"Portland Trail Blazers @ Los Angeles Lakers",
         "start":"2026-11-07T03:10:00Z","stat":"Points","line":31.5,
         "source":"BetMGM","direction":side}
        for side in ("More","Less")]}

def form():
    return {"players":[{"player":"Luka Dončić","player_id":"1629029","team":"LAL"}]}

class MarketCoverageTests(unittest.TestCase):
    def test_unicode_luka_coverage_and_no_double_count_from_sides(self):
        data=audit(odds(),form(),{"comparisons":[{
            "player_id":"1629029","stat":"PTS",
            "game":"Portland Trail Blazers @ Los Angeles Lakers"}]})
        game=next(iter(data["games"].values()))
        self.assertEqual(game["paired_listed_books"],1)
        self.assertEqual(game["paired_published_books"],1)
        self.assertEqual(game["coverage_pct"],100.0)
    def test_missing_luka_is_reported_not_invented(self):
        game=next(iter(audit(odds(),form(),{"comparisons":[]})["games"].values()))
        self.assertEqual(game["paired_published_books"],0)
        self.assertEqual(game["reasons"]["NOT_PUBLISHED"],1)
        self.assertEqual(game["missing_unique_player_markets"][0]["player"],"Luka Doncic")
    def test_absent_roster_not_autofilled(self):
        game=next(iter(audit(odds(),{"players":[]},{"comparisons":[]})["games"].values()))
        self.assertEqual(game["reasons"]["PLAYER_ABSENT_FROM_FORM"],1)
    def test_incomplete_one_sided_quote_not_counted(self):
        data=odds()
        data["picks"]=data["picks"][:1]
        self.assertFalse(audit(data,form(),{"comparisons":[]})["games"])

if __name__=="__main__":unittest.main()

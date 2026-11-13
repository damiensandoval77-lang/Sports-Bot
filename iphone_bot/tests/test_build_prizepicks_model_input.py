import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.build_prizepicks_model_input import convert

NOW=datetime(2026,11,8,17,tzinfo=timezone.utc)

def feed():
    begin=(NOW+timedelta(hours=3)).isoformat()
    observed=(NOW-timedelta(minutes=5)).isoformat()
    return {"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
      "provider_status":"fresh","generated_at":observed,
      "board_offers":[{"id":"p1","player":"Jayson Tatum","team":"BOS",
        "game":"Boston Celtics @ New York Knicks",
        "opponent":"NYK","stat":"PTS","line":26.5,
        "starts_at":begin,"observed_at":observed,
        "more_tier":"standard","less_tier":"standard","is_demo":False},
       {"id":"p2","player":"Jayson Tatum","team":"BOS",
        "game":"Boston Celtics @ New York Knicks","opponent":"NYK",
        "stat":"REB","line":7.5,"starts_at":begin,"observed_at":observed,
        "more_tier":"standard","less_tier":None,"is_demo":False}]}

class PrizePicksModelInputTests(unittest.TestCase):
    def test_real_pickem_lines_are_never_bogus_bookmaker_odds(self):
        d=convert(feed(),NOW)
        self.assertTrue(d["is_live"])
        self.assertEqual(d["status"],"FRESH_AUTHENTIC_PRIZEPICKS_LINES")
        self.assertEqual(len(d["picks"]),3)
        self.assertEqual({r["stat"] for r in d["picks"]},{"Points","Rebounds"})
        self.assertTrue(all(r["odds"] is None for r in d["picks"]))
        self.assertFalse(d["real_american_odds_provided"])
        self.assertEqual(d["upcoming_games"],1)
    def test_stale_or_post_tipoff_not_marked_live(self):
        old=feed();old["generated_at"]=(NOW-timedelta(hours=7)).isoformat()
        self.assertEqual(convert(old,NOW)["status"],"STALE_PROVIDER_BOARD")
        closed=feed()
        closed["board_offers"][0]["starts_at"]=(NOW-timedelta(minutes=1)).isoformat()
        closed["board_offers"][1]["starts_at"]=(NOW-timedelta(minutes=1)).isoformat()
        self.assertEqual(convert(closed,NOW)["status"],"NO_ELIGIBLE_UPCOMING_OFFERS")
    def test_wrong_team_and_demo_cannot_create_model_input(self):
        d=feed()
        d["board_offers"][0]["team"]="LAL"
        d["board_offers"][1]["is_demo"]=True
        got=convert(d,NOW)
        self.assertEqual(got["picks"],[])
        self.assertEqual(got["excluded_reasons"]["wrong_team"],1)
        self.assertEqual(got["excluded_reasons"]["unverified_live"],1)

if __name__=="__main__":unittest.main()

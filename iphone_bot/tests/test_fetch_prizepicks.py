import datetime as dt
import unittest
from iphone_bot.fetch_prizepicks import clean,match,publish

NOW=dt.datetime(2026,11,6,19,0,tzinfo=dt.timezone.utc)
START="2026-11-07T00:30:00Z"

def fixture():
    return {"id":"pp_123","source":"prizepicks","is_demo":False,"league":"NBA","status":"active",
            "player":{"name":"Sample Player","team":"BOS"},
            "event":{"opponent":"MIA","starts_at":START},
            "market":{"stat":"Points","period":"Full game"},
            "line":23.5,"observed_at":"2026-11-06T18:30:00Z",
            "selections":[{"side":"more","available":True,"tier":"standard"},
                          {"side":"less","available":True,"tier":"standard"}]}

COMP={"player":"Sample Player","team":"BOS","game":"Boston Celtics @ Miami Heat",
      "start":START,"stat":"PTS","projection":22.8,"combined_projection":24.0}

class PrizePicksTests(unittest.TestCase):
    def test_real_board_match(self):
        offer=clean(fixture(),NOW)
        self.assertTrue(match(offer,COMP,NOW))
        p=publish([{"data":[fixture()],"meta":{"mode":"live","source_status":"fresh","next_cursor":None}}],[COMP],NOW)
        self.assertEqual(p["matched_count"],1)
        self.assertEqual(p["offers"][0]["ai_direction"],"MORE")
        self.assertEqual(p["offers"][0]["more_tier"],"standard")

    def test_reject_demo_and_bad_period(self):
        demo=fixture();demo["is_demo"]=True
        self.assertIsNone(clean(demo,NOW))
        wrong=fixture();wrong["market"]["period"]="First Half"
        self.assertIsNone(clean(wrong,NOW))

    def test_unknown_opponent_uses_exact_tipoff(self):
        data=fixture();data["event"].pop("opponent")
        offer=clean(data,NOW)
        self.assertTrue(match(offer,COMP))
        later=dict(COMP,start="2026-11-07T01:10:00Z")
        self.assertFalse(match(offer,later,NOW))

    def test_demon_one_way(self):
        data=fixture();data["selections"]=[{"side":"more","available":True,"tier":"demon"}]
        offer=clean(data,NOW)
        self.assertEqual(offer["more_tier"],"demon")
        self.assertIsNone(offer["less_tier"])

    def test_bad_feed_refused(self):
        with self.assertRaises(ValueError):
            publish([{"data":[fixture()],"meta":{"mode":"demo","source_status":"fresh"}}],[COMP],NOW)

if __name__=="__main__":unittest.main()

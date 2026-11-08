import unittest
from datetime import datetime,timezone
from iphone_bot.publish_live_tracker_feed import build

GAME="Denver Nuggets @ Indiana Pacers"
AT=datetime(2026,11,8,1,30,tzinfo=timezone.utc)

def event(state="in"):
    return {"id":"401999111",
     "competitions":[{"competitors":[
       {"homeAway":"away","team":{"displayName":"Denver Nuggets"}},
       {"homeAway":"home","team":{"displayName":"Indiana Pacers"}}]}],
     "status":{"type":{"state":state,"shortDetail":"Q3 6:00"},
               "period":3,"displayClock":"6:00","clock":360}}

def summary(correct=True):
    home="Indiana Pacers" if correct else "Chicago Bulls"
    return {"header":{"competitions":[{"competitors":[
       {"homeAway":"away","team":{"displayName":"Denver Nuggets"}},
       {"homeAway":"home","team":{"displayName":home}}]}]},
      "boxscore":{"players":[{"team":{"abbreviation":"DEN"},
       "statistics":[{"labels":["PTS","REB","AST","MIN"],
         "athletes":[{"athlete":{"id":"203999","displayName":"Nikola Jokic"},
                     "stats":["22","8","10","29"]}]}]}]}}

class RealPlayerTrackingFallbackTests(unittest.TestCase):
    def test_original_verified_player_totals_and_time_are_preserved(self):
        r=build(AT,{"events":[event()]},{"401999111":summary()})
        self.assertEqual(r["status"],"OBSERVED_ESPN_LIVE_BOX_SCORES_SERVER_FALLBACK")
        self.assertEqual(len(r["games"]),1)
        g=r["games"][0]
        self.assertEqual(g["game"],GAME)
        self.assertEqual(g["state"],"in")
        self.assertEqual((g["period"],g["displayClock"]),(3,"6:00"))
        self.assertEqual(g["player_rows"][0]["PRA"],40)
        self.assertTrue(r["player_totals_are_observations"])
        self.assertTrue(r["not_ai_predictions"])
    def test_wrong_game_identity_rejected(self):
        r=build(AT,{"events":[event()]},{"401999111":summary(False)})
        self.assertEqual(r["games"],[])
        self.assertEqual(r["errors"][0]["reason"],"DIFFERENT_GAME")
    def test_no_pregame_live_player_totals_invented(self):
        r=build(AT,{"events":[event("pre")]},{"401999111":summary()})
        self.assertEqual(r["games"],[])
    def test_final_games_have_real_status_not_fake_pace(self):
        r=build(AT,{"events":[event("post")]},{"401999111":summary()})
        self.assertEqual(r["games"][0]["state"],"post")
if __name__=="__main__":unittest.main()

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

def summary(correct=True,state="in"):
    home="Indiana Pacers" if correct else "Chicago Bulls"
    return {"header":{"id":"401999111","competitions":[{"id":"401999111",
      "status":{"type":{"state":state,"shortDetail":"Final" if state=="post" else "Q3 6:00"},
                "period":4 if state=="post" else 3,"displayClock":"0:00" if state=="post" else "6:00"},"competitors":[
       {"homeAway":"away","score":"65","team":{"displayName":"Denver Nuggets"}},
       {"homeAway":"home","score":"67","team":{"displayName":home}}]}]},
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
    def test_newer_summary_clock_scores_and_state_are_source_coherent(self):
        old=event();old["status"].update(period=1,displayClock="12:00",clock=720)
        g=build(AT,{"events":[old]},{"401999111":summary()})["games"][0]
        self.assertEqual((g["period"],g["clock"],g["away_score"],g["home_score"]),(3,360,65,67))
        result=build(AT,{"events":[old]},{"401999111":summary(state="post")})
        self.assertEqual(result["games"][0]["state"],"post")
        self.assertTrue(result["coverage"]["complete"])

    def test_bad_summary_clock_keeps_real_totals_but_never_old_clock(self):
        for clock in (None,"12:99","13:00",12):
            s=summary();s["header"]["competitions"][0]["status"]["displayClock"]=clock
            g=build(AT,{"events":[event()]},{"401999111":s})["games"][0]
            self.assertIsNone(g["clock"]);self.assertIsNone(g["period"])
            self.assertEqual(g["player_rows"][0]["PTS"],22)

    def test_summary_id_mismatch_and_final_regression_rejected(self):
        for where in ("header","competition"):
            s=summary(); target=s["header"] if where=="header" else s["header"]["competitions"][0];target["id"]="999"
            self.assertEqual(build(AT,{"events":[event()]},{"401999111":s})["games"],[])
        self.assertEqual(build(AT,{"events":[event("post")]},{"401999111":summary()})["games"],[])

    def test_partial_live_coverage_is_reported_without_hiding_verified_games(self):
        second=event()
        second["id"]="401999112"
        second["competitions"][0]["competitors"][0]["team"]["displayName"]="Brooklyn Nets"
        second["competitions"][0]["competitors"][1]["team"]["displayName"]="Dallas Mavericks"
        data=build(AT,{"events":[event(),second]},{"401999111":summary()})
        self.assertEqual(data["coverage_status"],"PARTIAL_LIVE_DATA")
        self.assertEqual(data["coverage"]["missing_fresh_matchups"],
                         ["Brooklyn Nets @ Dallas Mavericks"])
        self.assertEqual(len(data["games"]),1)
    def test_preserves_stale_observation_but_not_as_fresh(self):
        old=build(AT,{"events":[event()]},{"401999111":summary()})
        now=AT.replace(minute=40)
        data=build(now,{"events":[event()]},{},old)
        self.assertEqual(data["coverage_status"],"PARTIAL_LIVE_DATA")
        self.assertEqual(data["games"][0]["observed_at"],AT.isoformat())
        self.assertTrue(data["games"][0]["stale"])
        self.assertIn(GAME,data["coverage"]["missing_fresh_matchups"])
    def test_does_not_reuse_stale_other_game_or_expired_data(self):
        old=build(AT,{"events":[event()]},{"401999111":summary()})
        later=AT.replace(hour=2,minute=15)
        data=build(later,{"events":[event()]},{},old)
        self.assertEqual(data["games"],[])
        self.assertFalse(data["coverage"]["complete"])

    def test_wrong_game_identity_rejected(self):
        r=build(AT,{"events":[event()]},{"401999111":summary(False)})
        self.assertEqual(r["games"],[])
        self.assertEqual(r["errors"][0]["reason"],"DIFFERENT_GAME")
    def test_no_pregame_live_player_totals_invented(self):
        r=build(AT,{"events":[event("pre")]},{"401999111":summary()})
        self.assertEqual(r["games"],[])
    def test_final_games_have_real_status_not_fake_pace(self):
        r=build(AT,{"events":[event("post")]},{"401999111":summary(state="post")})
        self.assertEqual(r["games"][0]["state"],"post")
if __name__=="__main__":unittest.main()

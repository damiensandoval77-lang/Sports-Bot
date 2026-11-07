import unittest
from iphone_bot.assist_shadow_v1 import assist_shadow
from iphone_bot.projection_upgrade_research import snapshot,grade_assist_shadow

NOW="2026-11-06T23:00:00Z"
EVENT="2026-11-07T01:00:00Z"
def history():
    return [{"id":"10","team":"BOS","date":f"2026-10-{day:02d}",
      "MIN":30.,"PTS":20.,"REB":6.,"AST":4.,"FGA":15.}
      for day in range(10,20)]
def board():
    return {"status":"EXPERIMENTAL_NON_CALIBRATED",
      "verified_current_matchups":True,"generated_at":"2026-11-06T22:55:00Z",
      "comparisons":[{"player":"Target Player","player_id":"10","team":"BOS",
         "stat":"AST","start":EVENT,"game":"Boston Celtics @ New York Knicks",
         "line":4.5,"projection":5.,"combined_projection":5.5}]}
def final_stat(line=4.5,actual=7):
    return [{"status":"SETTLED","event_start":EVENT,"captured_at":NOW,
      "player_id":"10","market":"AST","line":line,"actual":actual}]

class AssistResearchTests(unittest.TestCase):
    def test_only_prior_same_team_games(self):
        h=history()
        a=assist_shadow(h,"2026-11-06","BOS",6.,30.)
        future={**h[0],"date":"2026-11-06","AST":45.}
        other={**h[0],"date":"2026-10-21","team":"NYK","AST":45.}
        b=assist_shadow(h+[future,other],"2026-11-06","BOS",6.,30.)
        self.assertEqual(a["projection"],b["projection"])
        self.assertEqual(a["latest_prior_date"],"2026-10-19")
        self.assertEqual(a["status"],"PREGAME_LOCKED_ASSIST_CHALLENGER")
        self.assertLess(a["projection"],6.)
        self.assertFalse(a["live_applied"])

    def test_unstable_or_missing_history_fails_closed(self):
        self.assertIsNone(assist_shadow(history()[:3],"2026-11-06","BOS",6,30)["projection"])
        h=history()
        h[-1]["MIN"]=58.
        self.assertEqual(assist_shadow(h,"2026-11-06","BOS",6.,30.)["status"],
                         "UNSTABLE_RECENT_MINUTES_ROLE")
        self.assertIsNone(assist_shadow(history(),"2026-11-06","BOS",6.,None)["projection"])

    def test_pregame_freeze_and_exact_quote_settlement(self):
        frozen,_=snapshot(board(),{},[],NOW,history())
        self.assertEqual(frozen[0]["assist_shadow"]["status"],
                         "PREGAME_LOCKED_ASSIST_CHALLENGER")
        result=grade_assist_shadow(frozen,final_stat())
        self.assertEqual(result["paired_assist_markets"],1)
        self.assertEqual(result["baseline_correct_direction"],1)
        self.assertFalse(result["promoted"])
        self.assertEqual(grade_assist_shadow(frozen,final_stat(line=6))["paired_assist_markets"],0)
        without=[{**frozen[0],"assist_shadow":{"projection":None}}]
        self.assertEqual(grade_assist_shadow(without,final_stat())["paired_assist_markets"],0)

    def test_duplicate_bookmarket_not_scored_twice(self):
        saved,_=snapshot(board(),{},[],NOW,history())
        second={**saved[0],"captured_at":"2026-11-06T23:10:00+00:00"}
        result=grade_assist_shadow(saved+[second],final_stat())
        self.assertEqual(result["paired_assist_markets"],1)

if __name__=="__main__": unittest.main()

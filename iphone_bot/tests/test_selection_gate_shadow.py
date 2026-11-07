import unittest
from iphone_bot.selection_gate_shadow import pregame_gate
from iphone_bot.projection_upgrade_research import snapshot,grade_selection_gate

NOW="2026-11-06T23:00:00Z"
EVENT="2026-11-07T01:00:00Z"

def hist():
    return [{"id":"10","team":"BOS","date":f"2026-10-{day:02d}",
       "MIN":30.,"PTS":20.,"REB":6.,"AST":4.,"FGA":15.}
       for day in range(10,20)]

def board():
    return {"status":"EXPERIMENTAL_NON_CALIBRATED",
       "verified_current_matchups":True,"generated_at":"2026-11-06T22:55:00Z",
       "comparisons":[{"player":"Target Player","player_id":"10",
           "team":"BOS","stat":"PTS","start":EVENT,
           "game":"Boston Celtics @ New York Knicks",
           "line":20.5,"projection":22.,"combined_projection":23.,
           "shadow_projection":24.}]}

def injury():
    return {"status":"OFFICIAL_NBA_REPORT_VERIFIED",
       "injury_data_verified":True,"report_issued_at":"2026-11-06T22:30:00Z",
       "generated_at":"2026-11-06T22:40:00Z",
       "players":[{"player":"Teammate","player_id":"99","team":"BOS",
                   "game_date":"2026-11-06","status":"Out"}]}

def outcome(line=20.5,actual=25):
    return [{"status":"SETTLED","event_start":EVENT,
       "captured_at":NOW,"player_id":"10","market":"PTS",
       "original_projection":22.,"line":line,"actual":actual}]

class SelectionGateShadowTests(unittest.TestCase):
    def test_agreement_and_stable_minutes_research_eligible_only(self):
        r=pregame_gate("PTS",20.5,23,22,24,hist(),
                       {"status":"HISTORICAL_OPPORTUNITY_CANDIDATE"},
                       "OFFICIAL_SAME_DAY_VERIFIED")
        self.assertTrue(r["eligible"])
        self.assertFalse(r["wager_recommended"])
        self.assertFalse(r["probability_calibrated"])

    def test_disagreement_and_volatility_abstain(self):
        games=hist()
        games[-1]["MIN"]=10
        result=pregame_gate("PTS",20.5,23,19,26,games,
                           {"status":"HISTORICAL_OPPORTUNITY_CANDIDATE"},
                           "OFFICIAL_SAME_DAY_VERIFIED")
        self.assertFalse(result["eligible"])
        self.assertIn("ORIGINAL_AND_OPPONENT_MODELS_DISAGREE_ON_SIDE",result["reasons"])
        self.assertIn("VOLATILE_LAST5_MINUTES",result["reasons"])

    def test_no_history_and_missing_verified_injury_status_abstain(self):
        r=pregame_gate("AST",5.5,7,8,9,hist()[:4],
                       {"status":"INSUFFICIENT_PRIOR_SAME_TEAM_GAMES"},
                       "NO_SAME_DAY_PLAYER_STATUS")
        self.assertIn("INSUFFICIENT_PREGAME_PLAYER_HISTORY",r["reasons"])
        self.assertIn("NO_VERIFIED_SAME_DAY_INJURY_REPORT",r["reasons"])

    def test_shadow_freeze_ignores_future_game_and_never_rewrites_existing(self):
        first,_=snapshot(board(),injury(),[],NOW,hist())
        self.assertTrue(first[0]["selection_gate"]["eligible"])
        future={"id":"10","team":"BOS","date":"2026-11-06",
                "MIN":1.,"PTS":1.,"REB":1.,"AST":1.,"FGA":1.}
        second,_=snapshot(board(),injury(),[],NOW,hist()+[future])
        self.assertEqual(first[0]["selection_gate"],second[0]["selection_gate"])
        changed=board()
        changed["comparisons"][0]["shadow_projection"]=1.
        saved,counts=snapshot(changed,injury(),first,NOW,hist())
        self.assertEqual(saved,first)
        self.assertEqual(counts.get("new",0),0)

    def test_exact_saved_bookmaker_line_required_to_grade_shadow(self):
        locked,_=snapshot(board(),injury(),[],NOW,hist())
        graded=grade_selection_gate(locked,outcome())
        self.assertEqual(graded["selected"]["wins"],1)
        self.assertEqual(graded["all_evaluated"]["markets"],1)
        self.assertFalse(graded["sufficient_prospective_validation"])
        self.assertEqual(grade_selection_gate(locked,outcome(21.5))["all_evaluated"]["markets"],0)
        self.assertEqual(grade_selection_gate([],outcome())["all_evaluated"]["markets"],0)

if __name__=="__main__": unittest.main()

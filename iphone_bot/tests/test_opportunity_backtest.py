import unittest
from iphone_bot.opportunity_backtest import (
    histories,opportunity,candidate,stability_candidate,evaluate,describe)

def history(player="7",team="BOS"):
    result=[]
    for n in range(1,11):
        result.append({"id":player,"team":team,
           "date":f"2026-10-{n+10:02d}",
           "MIN":25+n/2,"PTS":12+n/2,"REB":3+n/4,
           "AST":2+n/5,"FGA":8+n/2})
    return result

def locked(actual=24):
    return {"status":"SETTLED","player_id":"7","player":"Test Player",
        "team":"BOS","game":"Boston Celtics @ Charlotte Hornets",
        "event_start":"2026-11-07T00:10:00Z",
        "captured_at":"2026-11-06T21:00:00Z",
        "bookmaker":"FanDuel","market":"PTS","line":20.5,
        "combined_projection":22.0,"original_projection":21.0,
        "opponent_shadow_projection":23.0,
        "actual":actual}

class OpportunityBacktestTests(unittest.TestCase):
    def test_history_strictly_before_game_and_same_team(self):
        h=histories(history()+[
            {"**bad":1},
            {"id":"7","team":"BOS","date":"2026-11-06",
             "MIN":45,"PTS":100,"REB":50,"AST":30,"FGA":40},
            {"id":"7","team":"CHA","date":"2026-10-17",
             "MIN":30,"PTS":99,"REB":20,"AST":10,"FGA":40}
        ])
        a=opportunity(h[("7","BOS")],"2026-11-06","BOS")
        b=opportunity(histories(history())[("7","BOS")],"2026-11-06","BOS")
        self.assertEqual(a["raw_stat_projections"],b["raw_stat_projections"])
        self.assertEqual(a["expected_minutes"],b["expected_minutes"])
        self.assertEqual(a["prior_latest_game_date"],"2026-10-20")
        self.assertTrue(a["usage_fga_ratio_clamped"]<=1.1)

    def test_empty_or_short_history_fails_closed(self):
        self.assertEqual(opportunity(history()[:4],"2026-11-06","BOS")["status"],
                         "INSUFFICIENT_PRIOR_SAME_TEAM_GAMES")
        r=evaluate([locked()],history()[:4])
        self.assertEqual(r["overall"]["sample_size"],0)
        self.assertEqual(r["missing"]["insufficient_prior_history"],1)

    def test_candidate_blend_bounded_and_not_mutated(self):
        self.assertEqual(candidate(20,40),23)
        self.assertEqual(candidate(20,0),17)
        self.assertEqual(candidate(None,40),None)
        original=locked()
        d=evaluate([original],history())
        self.assertEqual(d["retrospective_candidates"],1)
        self.assertFalse(d["prospective_validation"])
        self.assertTrue(d["live_combined_ai_unchanged"])
        self.assertEqual(original["combined_projection"],22)
        self.assertEqual(d["examples"][0]["actual"],24)
        self.assertLess(d["examples"][0]["last_prior_game"],"2026-11-06")

    def test_duplicate_books_same_prop_only_once(self):
        x=locked()
        y={**x,"bookmaker":"DraftKings",
           "captured_at":"2026-11-06T22:00:00Z","line":19.5}
        report=evaluate([x,y],history())
        self.assertEqual(report["overall"]["sample_size"],1)

    def test_missing_fga_does_not_invent_usage(self):
        games=[dict(x,FGA=None) for x in history()]
        out=opportunity(games,"2026-11-06","BOS")
        self.assertIsNone(out["expected_fga"])
        self.assertEqual(out["usage_fga_ratio_clamped"],1.0)

    def test_stability_candidate_shrinks_volatile_minutes_without_lookahead(self):
        stable=stability_candidate(20,40,{"last5_minutes_volatility":2})
        volatile=stability_candidate(20,40,{"last5_minutes_volatility":12})
        self.assertEqual(stable,23)
        self.assertGreater(volatile,20)
        self.assertLess(volatile,stable)
        self.assertIsNone(stability_candidate(20,40,{}))
        self.assertIsNone(stability_candidate(None,40,{"last5_minutes_volatility":9}))
        out=opportunity(history(),"2026-11-06","BOS")
        self.assertIn("last5_minutes_volatility",out)
        self.assertAlmostEqual(out["raw_stat_projections"]["PRA"],
            sum(out["raw_stat_projections"][m] for m in ("PTS","REB","AST")),places=3)

    def test_direction_and_mae(self):
        d=describe([{"baseline":20.0,"candidate":21.0,
          "actual":23.0,"line":20.5}])
        self.assertEqual(d["baseline_mae"],3)
        self.assertEqual(d["candidate_mae"],2)
        self.assertEqual(d["mae_change"],-1)
        self.assertEqual(d["candidate_wins"],1)
        self.assertEqual(d["baseline_losses"],1)

if __name__=="__main__":unittest.main()

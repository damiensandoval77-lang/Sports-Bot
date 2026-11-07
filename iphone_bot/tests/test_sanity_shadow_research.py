import unittest
from iphone_bot.sanity_shadow_research import shadow,capture,report,METHOD

CAPTURE="2026-11-07T16:00:00Z"
TIP="2026-11-08T01:00:00Z"

def games(values=(40,42,44,41,43,42,40,44,41,43),team="DEN"):
    return [{"id":"p1","team":team,"date":f"2026-10-{i+15:02d}",
             "PTS":p,"REB":7,"AST":8,"PRA":p+15,"MIN":34}
            for i,p in enumerate(values)]

def run(history=None,**kw):
    x={"team":"DEN","market":"PTS","baseline":28,
       "event_start":TIP,"captured_at":CAPTURE,
       "minutes_context":{"expected_minutes":34},"injury_status":"AVAILABLE",
       "injury_source":"OFFICIAL_NBA_REPORT"}
    x.update(kw)
    return shadow(games() if history is None else history,**x)

class SanityShadowTests(unittest.TestCase):
    def test_large_deviation_produces_bounded_shadow_not_live(self):
        r=run()
        self.assertEqual(r["status"],"SHADOW_CANDIDATE_UNVALIDATED")
        self.assertIn("LARGE_SEASON_BASELINE_DEVIATION",r["warnings"])
        self.assertLessEqual(r["shadow_projection"]-28,2.8+1e-5)
        self.assertGreater(r["shadow_projection"],28)
        self.assertFalse(r["live_applied"])
        self.assertFalse(r["simulated_probability_changed"])

    def test_no_large_deviation_keeps_original(self):
        r=run(baseline=42)
        self.assertEqual(r["status"],"NO_LARGE_DEVIATION")
        self.assertEqual(r["shadow_projection"],42)

    def test_unknown_injury_stops_adjustment(self):
        r=run(injury_status="UNKNOWN")
        self.assertEqual(r["status"],"REVIEW_ONLY_UNCERTAIN_INPUTS")
        self.assertIsNone(r["shadow_projection"])
        self.assertIn("INJURY_OR_LINEUP_UNCERTAINTY",r["warnings"])

    def test_inconsistent_minutes_stops_adjustment(self):
        r=run(minutes_context={"expected_minutes":20})
        self.assertEqual(r["status"],"REVIEW_ONLY_UNCERTAIN_INPUTS")
        self.assertIn("EXPECTED_MINUTES_DISAGREE_WITH_RECENT",r["warnings"])

    def test_volatile_minutes_blocks_shadow_even_when_mean_matches(self):
        history=games()
        for i,g in enumerate(history[-5:]):
            g["MIN"]=[20,40,20,40,30][i]
        r=run(history=history,minutes_context={"expected_minutes":30})
        self.assertEqual(r["status"],"REVIEW_ONLY_UNCERTAIN_INPUTS")
        self.assertIn("HIGH_RECENT_MINUTES_VOLATILITY",r["warnings"])

    def test_stale_player_history_blocks_shadow(self):
        r=run(captured_at="2026-11-10T16:00:00Z",
              event_start="2026-11-11T01:00:00Z")
        self.assertEqual(r["status"],"REVIEW_ONLY_UNCERTAIN_INPUTS")
        self.assertIn("STALE_PLAYER_HISTORY",r["warnings"])

    def test_missing_minutes_stops_adjustment(self):
        self.assertEqual(run(minutes_context={})["status"],"REVIEW_ONLY_UNCERTAIN_INPUTS")

    def test_unverified_available_does_not_allow_adjustment(self):
        r=run(injury_source="ESPN_THIRD_PARTY_NOT_CONFIRMED")
        self.assertEqual(r["status"],"REVIEW_ONLY_UNCERTAIN_INPUTS")

    def test_previous_season_is_not_used_as_current_season(self):
        old=[{**g,"date":g["date"].replace("2026","2025")} for g in games()]
        r=run(history=old)
        self.assertEqual(r["status"],"INSUFFICIENT_PREGAME_HISTORY")

    def test_future_and_same_day_games_excluded(self):
        future=games()+[{"id":"p1","team":"DEN","date":"2026-11-07","PTS":150,"MIN":34}]
        r=run(history=future)
        self.assertEqual(r["history_games"],10)
        self.assertLess(r["season_average"],50)

    def test_conflicting_duplicate_date_excluded_even_if_repeated(self):
        history=games()
        a={**history[0],"PTS":89}
        r=run(history=history+[a,history[0]])
        self.assertEqual(r["history_games"],9)

    def test_insufficient_history_leaves_shadow_unavailable(self):
        r=run(history=games()[:4])
        self.assertEqual(r["status"],"INSUFFICIENT_PREGAME_HISTORY")
        self.assertIsNone(r["shadow_projection"])

    def test_pra_components_and_inconsistent_totals(self):
        h=games()
        for g in h:g.pop("PRA")
        r=run(history=h,market="PRA",baseline=30)
        self.assertEqual(r["history_games"],10)
        h[0]["PRA"]=999
        r=run(history=h,market="PRA",baseline=30)
        self.assertEqual(r["history_games"],9)

    def test_late_capture_rejected(self):
        self.assertEqual(run(captured_at="2026-11-08T02:00:00Z")["status"],"LATE_CAPTURE_REJECTED")

    def test_unverified_board_rejected(self):
        board={"generated_at":"2026-11-07T15:50:00Z","status":"EXPERIMENTAL_NON_CALIBRATED",
               "verified_current_matchups":False,"comparisons":[]}
        with self.assertRaises(ValueError):capture(board,games(),[],CAPTURE)

    def test_immutable_capture_and_multi_book_independence(self):
        board={"generated_at":"2026-11-07T15:50:00Z","status":"EXPERIMENTAL_NON_CALIBRATED",
               "verified_current_matchups":True,
               "comparisons":[{"player_id":"p1","player":"Player","team":"DEN",
                 "stat":"PTS","start":TIP,"game":"Denver Nuggets @ Indiana Pacers",
                 "combined_projection":28,"line":31.5,"minutes_research":{"expected_minutes":34},
                 "injury_status":"AVAILABLE","injury_status_source":"OFFICIAL_NBA_REPORT"}]}
        before=capture(board,games(),[],CAPTURE)
        self.assertEqual(len(before),1)
        board["comparisons"][0]["combined_projection"]=5
        again=capture(board,games(),before,"2026-11-07T16:10:00Z")
        self.assertEqual(len(again),1)
        self.assertEqual(again[0]["combined_projection"],28)
        self.assertEqual(again[0]["shadow"]["method"],METHOD)
        self.assertTrue(report(again)["no_picks_changed"])

    def test_invalid_probability_not_invented(self):
        r=run()
        self.assertNotIn("simulated_hit_probability",r)
        self.assertFalse(r["simulated_probability_changed"])

if __name__=="__main__":unittest.main()

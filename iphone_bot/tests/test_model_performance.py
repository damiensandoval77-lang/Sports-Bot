import unittest
from iphone_bot.model_performance import compute_performance,forecast_values

def settled(player="1",book="FanDuel",line=20.5,actual=23,original=22,shadow=19,combined=None,
            over=-110,under=-110,captured="2026-11-12T19:00:00Z"):
    row={"status":"SETTLED","event_start":"2026-11-13T00:30:00Z",
        "captured_at":captured,"player_id":player,"team":"BOS",
        "market":"PTS","bookmaker":book,"line":line,"actual":actual,
        "original_projection":original,"opponent_shadow_projection":shadow,
        "over_odds":over,"under_odds":under,"side":"OVER",
        "american_odds":over if over is not None else -110}
    if combined is not None:row["combined_projection"]=combined
    return row

class ModelPerformanceTests(unittest.TestCase):
    def test_three_models_same_real_game(self):
        r=compute_performance([settled()])
        self.assertEqual(r["independent_settled_markets"],1)
        a,b,c=[r["models"][x] for x in ("original","opponent_aware","combined")]
        self.assertEqual([x["observations"] for x in (a,b,c)],[1,1,1])
        self.assertEqual([x["mae"] for x in (a,b,c)],[1,4,2.5])
        self.assertEqual([x["direction_hit_rate"] for x in (a,b,c)],[1,0,1])
        self.assertEqual([x["priced_paper_selections"] for x in (a,b,c)],[1,1,1])
        self.assertGreater(a["paper_profit_units"],0)
        self.assertEqual(b["paper_profit_units"],-1)

    def test_duplicate_sportsbooks_do_not_inflate_sample(self):
        initial=settled()
        second=settled(book="DraftKings",over=120,under=120,captured="2026-11-12T20:00:00Z")
        r=compute_performance([second,initial])
        self.assertEqual(r["independent_settled_markets"],1)
        self.assertEqual(r["models"]["original"]["observations"],1)
        self.assertAlmostEqual(r["models"]["original"]["paper_profit_units"],100/110,places=4)

    def test_missing_opposite_odds_never_reuses_wrong_price(self):
        old=settled(shadow=19,over=None,under=None)
        # Legacy only stored OVER quote; opponent predicts UNDER.
        r=compute_performance([old])
        self.assertEqual(r["models"]["opponent_aware"]["direction_losses"],1)
        self.assertEqual(r["models"]["opponent_aware"]["priced_paper_selections"],0)
        self.assertIsNone(r["models"]["opponent_aware"]["paper_roi_per_priced_unit"])
        self.assertEqual(r["models"]["original"]["priced_paper_selections"],1)

    def test_push_excluded_from_hit_rate(self):
        r=compute_performance([settled(line=23,actual=23,original=24,shadow=22)])
        self.assertEqual(r["models"]["original"]["direction_pushes"],1)
        self.assertIsNone(r["models"]["original"]["direction_hit_rate"])
        self.assertEqual(r["models"]["original"]["paper_profit_units"],0)

    def test_missing_shadow_no_invented_combined(self):
        r=compute_performance([settled(shadow=None,combined=22)])
        self.assertEqual(r["models"]["original"]["observations"],1)
        self.assertEqual(r["models"]["combined"]["observations"],0)
        self.assertEqual(r["models"]["opponent_aware"]["observations"],0)

    def test_pending_late_and_missing_actual_excluded(self):
        pending=settled();pending["status"]="PENDING"
        late=settled(player="2",captured="2026-11-13T01:00:00Z")
        absent=settled(player="3");absent.pop("actual")
        r=compute_performance([pending,late,absent])
        self.assertEqual(r["independent_settled_markets"],0)
        self.assertIsNone(r["models"]["original"]["mae"])

    def test_no_retrained_forecast_overwrite(self):
        row=settled(original=22,shadow=18,combined=20)
        self.assertEqual(forecast_values(row),{"original":22,"opponent_aware":18,"combined":20})

if __name__=="__main__":unittest.main()

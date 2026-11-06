import unittest
from iphone_bot.paper_pick_pipeline import snapshot,settle,summary

class PaperPipelineTests(unittest.TestCase):
    def market(self):
        return {"player":"Sample Player","player_id":"123","team":"BOS",
          "game":"Boston Celtics @ Miami Heat","start":"2026-11-13T00:30:00Z",
          "stat":"PTS","projection":24.2,"shadow_projection":23.8,
          "book_quotes":[{"name":"FanDuel","line":22.5,"over":-110,"under":-120,
                          "over_model_probability":.6,"hypothetical_over_ev_pct":14.5},
                         {"name":"DraftKings","line":25.5,"over":+110,"under":-115,
                          "under_model_probability":.57,"hypothetical_under_ev_pct":6.3}]}
    def game(self,points=23):
        return {"id":"123","date":"2026-11-12","team":"BOS","opponent":"MIA",
                "PTS":points,"REB":5,"AST":4,"PRA":points+9,"MIN":30}
    def test_freeze_before_start_and_settle_real_book_price(self):
        market=self.market()
        at="2026-11-12T18:00:00Z"
        first=snapshot([market],at)
        self.assertEqual(len(first),2)
        self.assertEqual({r["side"] for r in first},{"OVER","UNDER"})
        self.assertEqual(len(snapshot([market],"2026-11-12T21:00:00Z",first)),2)
        # One game is one win and one loss at the two different quoted lines.
        graded=settle(first,[self.game(23)],"2026-11-13T07:00:00Z")
        outcome={r["bookmaker"]:r for r in graded}
        self.assertEqual(outcome["FanDuel"]["result"],"WIN")
        self.assertEqual(outcome["DraftKings"]["result"],"WIN")
        self.assertAlmostEqual(outcome["FanDuel"]["paper_profit_units"],.909091,places=5)
        self.assertAlmostEqual(outcome["DraftKings"]["paper_profit_units"],100/115,places=5)
        self.assertEqual(summary(graded)["settled"],2)
        self.assertEqual(summary(graded)["independent_player_game_markets"],1)
    def test_nonfinite_and_incomplete_boxscores_never_get_graded(self):
        rows=snapshot([self.market()],"2026-11-12T20:00:00Z")
        for bad in (dict(self.game(),MIN=0),
                    dict(self.game(),MIN=75),
                    dict(self.game(),PTS=float("nan")),
                    dict(self.game(),PTS=-2)):
            settled=settle(rows,[bad],"2026-11-13T07:00:00Z")
            self.assertTrue(all(x["status"]=="PENDING" for x in settled))

    def test_pra_inconsistency_remains_pending(self):
        market=self.market()
        market["stat"]="PRA"
        rows=snapshot([market],"2026-11-12T20:00:00Z")
        bad=dict(self.game(),PRA=100)
        settled=settle(rows,[bad],"2026-11-13T07:00:00Z")
        self.assertTrue(all(x["status"]=="PENDING" for x in settled))

    def test_ambiguous_duplicate_player_games_not_graded(self):
        rows=snapshot([self.market()],"2026-11-12T20:00:00Z")
        settled=settle(rows,[self.game(23),self.game(24)],"2026-11-13T07:00:00Z")
        self.assertTrue(all(x["status"]=="PENDING" for x in settled))

    def test_nonfinite_pregame_forecast_is_not_locked(self):
        for forecast in (float("nan"),float("inf"),-1):
            market=self.market()
            market["projection"]=forecast
            self.assertEqual(snapshot([market],"2026-11-12T20:00:00Z"),[])

    def test_json_and_python_utc_format_are_same_immutable_pick(self):
        first=snapshot([self.market()],"2026-11-12T20:00:00Z")
        mixed=[dict(row,event_start=row["event_start"].replace("+00:00",".000Z"))
               for row in first]
        new=snapshot([self.market()],"2026-11-12T21:00:00+00:00",mixed+first)
        self.assertEqual(len(new),2)
        self.assertEqual({r["bookmaker"] for r in new},{"FanDuel","DraftKings"})

    def test_do_not_retrofit_late_predictions(self):
        self.assertEqual(snapshot([self.market()],"2026-11-13T00:31:00Z"),[])
    def test_missing_boxscore_is_pending_not_loss(self):
        pending=snapshot([self.market()],"2026-11-12T20:00:00Z")
        rows=settle(pending,[],"2026-11-13T12:00:00Z")
        self.assertEqual(len(rows),2)
        self.assertEqual(summary(rows)["settled"],0)
        self.assertEqual(summary(rows)["pending"],2)
    def test_wrong_team_or_opponent_not_settled(self):
        pending=snapshot([self.market()],"2026-11-12T20:00:00Z")
        mismatch=dict(self.game(),opponent="NYK")
        self.assertTrue(all(x["status"]=="PENDING" for x in
            settle(pending,[mismatch],"2026-11-13T12:00:00Z")))
    def test_push_refunds_paper_unit(self):
        market=self.market()
        market["projection"]=24
        market["book_quotes"]=[{"name":"Book","line":23,"over":100,"under":-110}]
        pending=snapshot([market],"2026-11-12T20:00:00Z")
        r=settle(pending,[self.game(23)],"2026-11-13T12:00:00Z")
        self.assertEqual(r[0]["result"],"PUSH")
        self.assertEqual(r[0]["paper_profit_units"],0)
    def test_snapshot_keeps_original_prediction_when_changed_later(self):
        old=snapshot([self.market()],"2026-11-12T20:00:00Z")
        changed=self.market()
        changed["projection"]=11
        changed["book_quotes"][0]["over"]=-200
        after=snapshot([changed],"2026-11-12T22:00:00Z",old)
        self.assertEqual(len(after),2) # One immutable original side per exact book and line.
        original=[r for r in after if r["bookmaker"]=="FanDuel" and r["side"]=="OVER"][0]
        self.assertEqual(original["american_odds"],-110)
        self.assertEqual(original["original_projection"],24.2)

if __name__=="__main__":unittest.main()

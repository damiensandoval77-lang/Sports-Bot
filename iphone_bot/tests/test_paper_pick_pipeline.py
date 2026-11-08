import unittest
from iphone_bot.paper_pick_pipeline import snapshot,settle,summary,cross_checked_final_boxscores

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
    def test_minutes_v3_and_opportunity_v2_are_originally_frozen(self):
        m=self.market()
        m["stat"]="AST"
        m["minutes_v3_research"]={
           "status":"PREGAME_MINUTES_V3_RESEARCH",
           "expected_minutes":31.2,"last_prior_date":"2026-11-11",
           "production_applied":False}
        m["opportunity_v2_research"]={"markets":{"AST":{
           "status":"PREGAME_OPPORTUNITY_V2_RESEARCH",
           "projection":7.1,"last_prior_game":"2026-11-11",
           "source_kind":"BOX_SCORE_RATE_PROXY"}}}
        saved=snapshot([m],"2026-11-12T18:00:00Z")
        self.assertEqual(len(saved),2)
        self.assertEqual(saved[0]["minutes_v3_research"]["expected_minutes"],31.2)
        self.assertEqual(saved[0]["opportunity_v2_research"]["markets"]["AST"]["projection"],7.1)
        m["minutes_v3_research"]["expected_minutes"]=100
        m["opportunity_v2_research"]["markets"]["AST"]["projection"]=100
        again=snapshot([m],"2026-11-12T18:10:00Z",saved)
        self.assertEqual(again[0]["minutes_v3_research"]["expected_minutes"],31.2)
        self.assertEqual(again[0]["opportunity_v2_research"]["markets"]["AST"]["projection"],7.1)

    def test_shooting_v1_shadow_is_frozen_and_immutable(self):
        m=self.market()
        m["shooting_efficiency_v1"]={
            "status":"PREGAME_SHOOTING_SHADOW_RESEARCH",
            "projection":24.5,"blended_projection":23.8,
            "last_prior_game":"2026-11-11",
            "production_applied":False}
        stored=snapshot([m],"2026-11-12T18:00:00Z")
        self.assertEqual(len(stored),2)
        self.assertEqual(stored[0]["shooting_efficiency_v1"]["projection"],24.5)
        m["shooting_efficiency_v1"]["projection"]=100
        self.assertEqual(stored[0]["shooting_efficiency_v1"]["projection"],24.5)
        again=snapshot([m],"2026-11-12T19:00:00Z",stored)
        self.assertEqual(again[0]["shooting_efficiency_v1"]["projection"],24.5)

    def test_verified_third_party_final_settles_celtics_only(self):
        from pathlib import Path
        verified=Path(__file__).resolve().parents[2]/"docs/verified_postgame_boxscores.json"
        checked=cross_checked_final_boxscores(verified)
        tatum=next(x for x in checked if x["player"]=="Jayson Tatum")
        self.assertEqual((tatum["PTS"],tatum["REB"],tatum["AST"]),(34,8,9))
        p=self.market()
        p.update(player="Jayson Tatum",player_id="1628369",
                 game="Boston Celtics @ Charlotte Hornets",
                 start="2026-11-07T00:10:00Z",
                 projection=30,combined_projection=31)
        items=snapshot([p],"2026-11-06T22:00:00Z")
        graded=settle(items,checked,"2026-11-07T03:10:00Z")
        self.assertEqual(len(graded),2)
        self.assertTrue(all(row["status"]=="SETTLED" for row in graded))
        self.assertTrue(all(row["settlement_source"]=="CBS_FINAL_VERIFIED" for row in graded))
        before=settle(items,checked,"2026-11-07T01:00:00Z")
        self.assertTrue(all(row["status"]=="PENDING" for row in before))

    def test_official_final_can_settle_before_three_hour_delay(self):
        picks=snapshot([self.market()],"2026-11-12T20:00:00Z")
        game={**self.game(24),"player":"Sample Player","source":"NBA_CDN_FINAL",
              "final_confirmed":True,"source_game_id":"0022600030"}
        # 2h15 from game start; status must be independently confirmed final.
        graded=settle(picks,[game],"2026-11-13T02:45:00Z")
        self.assertTrue(all(r["status"]=="SETTLED" for r in graded))
        not_final={**game,"final_confirmed":False}
        waiting=settle(picks,[not_final],"2026-11-13T02:45:00Z")
        self.assertTrue(all(r["status"]=="PENDING" for r in waiting))

    def test_official_final_explicit_dnp_is_void_not_loss(self):
        picks=snapshot([self.market()],"2026-11-12T20:00:00Z")
        dnp={"player":"Sample Player","team":"BOS","opponent":"MIA",
             "date":"2026-11-12","source":"NBA_CDN_FINAL",
             "source_game_id":"0022600030","final_confirmed":True,
             "dnp_final_verified":True,"dnp_reason":"INACTIVE"}
        void=settle(picks,[dnp],"2026-11-13T03:00:00Z")
        self.assertTrue(all(r["status"]=="VOID_DNP" for r in void))
        self.assertTrue(all(r["result"]=="VOID" for r in void))
        report=summary(void)
        self.assertEqual(report["void_dnp"],2)
        self.assertEqual(report["settled"],0)
        self.assertIsNone(report["win_rate_ex_push"])
        waiting=settle(picks,[dnp],"2026-11-13T01:30:00Z")
        self.assertTrue(all(r["status"]=="PENDING" for r in waiting))

    def test_independent_pending_and_combined_record_excludes_duplicate_books(self):
        from iphone_bot.model_performance import compute_performance
        rows=snapshot([self.market()],"2026-11-12T20:00:00Z")
        pending_report=summary(rows)
        self.assertEqual(pending_report["pending"],2)
        self.assertEqual(pending_report["independent_pending_player_game_markets"],1)
        self.assertIsNone(pending_report["performance"]["models"]["combined"]["direction_hit_rate"])
        graded=settle(rows,[self.game(23)],"2026-11-13T07:00:00Z")
        finished=summary(graded)
        self.assertEqual(finished["independent_player_game_markets"],1)
        self.assertEqual(finished["independent_pending_player_game_markets"],0)
        combined=finished["performance"]["models"]["combined"]
        self.assertEqual(combined["direction_wins"]+combined["direction_losses"],1)
        self.assertEqual(combined["observations"],1)

    def test_snapshot_freezes_quote_specific_original_probability(self):
        data=self.market()
        data["projection"]=24.2
        data["combined_projection"]=18.0
        data["combined_model_count"]=2
        data["book_quotes"][0]["over_model_probability"]=0.72
        data["book_quotes"][0]["under_model_probability"]=0.28
        locked=snapshot([data],"2026-11-12T20:00:00Z")
        fanduel=next(x for x in locked if x["bookmaker"]=="FanDuel")
        self.assertEqual(fanduel["side"],"UNDER")
        self.assertEqual(fanduel["original_probability_side"],"OVER")
        self.assertEqual(fanduel["original_probability_estimate"],0.72)
        second=snapshot([data],"2026-11-12T21:00:00Z",locked)
        self.assertEqual(second[0]["captured_at"],locked[0]["captured_at"])
        self.assertEqual(second[0]["original_probability_estimate"],locked[0]["original_probability_estimate"])

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
    def test_freezes_original_residual_proxy_for_combined_direction_before_tip(self):
        data=self.market()
        data["projection"]=18.0
        data["combined_projection"]=26.0
        data["combined_model_count"]=2
        data["book_quotes"][0]["over_model_probability"]=.31
        data["book_quotes"][0]["under_model_probability"]=.69
        rows=snapshot([data],"2026-11-12T20:00:00Z")
        fanduel=next(x for x in rows if x["bookmaker"]=="FanDuel")
        self.assertEqual(fanduel["side"],"OVER")
        self.assertEqual(fanduel["combined_probability_proxy_side"],"OVER")
        self.assertEqual(fanduel["combined_probability_proxy_estimate"],.31)
        self.assertEqual(fanduel["original_probability_side"],"UNDER")
        self.assertEqual(fanduel["original_probability_estimate"],.69)
        changed=self.market()
        changed["projection"]=40
        changed["combined_projection"]=10
        still=snapshot([changed],"2026-11-12T21:00:00Z",rows)
        saved=next(x for x in still if x["bookmaker"]=="FanDuel")
        self.assertEqual(saved["combined_probability_proxy_estimate"],.31)

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

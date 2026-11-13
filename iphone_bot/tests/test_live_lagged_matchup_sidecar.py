"""Live challenger must reject stale lines and avoid invented projection confidence."""
from datetime import datetime,timezone
import unittest
try:
    from iphone_bot.live_lagged_matchup_sidecar import forecast,current_games,build_features,standard_points_offers
except ImportError:
    from live_lagged_matchup_sidecar import forecast,current_games,build_features

class FakeModel:
    def predict(self,arr):return [21.5]

class SidecarTests(unittest.TestCase):
    def test_source_crosscheck_only(self):
        local=[{"id":"123","team":"BOS","date":"2026-11-01","player":"Sample Player",
                "PTS":20,"REB":5,"AST":4,"MIN":30,"opponent":"NYK"}]
        source=[{"id":"123","team":"BOS","date":"2026-11-01","pts":20,"reb":5,
                 "ast":4,"minutes":30,"fga":13,"fta":5,"tov":2,"oreb":1}]
        rows,health=current_games(local,source)
        self.assertEqual(health["MATCHED"],1)
        self.assertEqual(rows[0]["FTA"],5)
        self.assertEqual(rows[0]["OREB"],1)

    def test_rounded_subminute_cameo_does_not_poison_eight_eligible_games(self):
        # The CSV rounds a 56-second appearance up to 1 minute. Keep the
        # independently crosschecked duration, but exclude this ineligible
        # row rather than letting it invalidate the player's entire history.
        local=[]
        source=[]
        for i in range(1,10):
            local.append({"id":"123","team":"BOS","date":f"2026-11-{i:02d}",
                          "player":"Sample Player","opponent":"NYK",
                          "PTS":0 if i==1 else 20,"REB":0 if i==1 else 5,
                          "AST":0 if i==1 else 4,"MIN":1 if i==1 else 30})
            source.append({"id":"123","team":"BOS","date":f"2026-11-{i:02d}",
                           "pts":0 if i==1 else 20,"reb":0 if i==1 else 5,
                           "ast":0 if i==1 else 4,"minutes":56/60 if i==1 else 30,
                           "fga":0 if i==1 else 13,"fta":0 if i==1 else 5,
                           "tov":0 if i==1 else 2,"oreb":0 if i==1 else 1})
        rows,health=current_games(local,source)
        self.assertEqual(len(rows),8)
        self.assertEqual(health["BELOW_MODEL_MINIMUM_MINUTES"],1)
        self.assertEqual(health["MATCHED"],8)
        features,reason=build_features(rows,"BOS","NYK","2026-11-12",{},
                                       neutral_defense_on_missing=True)
        self.assertIsNone(reason)
        self.assertEqual(features["history_count"],8)
        # Seven real eligible games remain insufficient. Never count or
        # round up the cameo just to satisfy the model history threshold.
        features,reason=build_features(rows[:-1],"BOS","NYK","2026-11-12",{},
                                       neutral_defense_on_missing=True)
        self.assertIsNone(features)
        self.assertEqual(reason,"INSUFFICIENT_PLAYER_OPPORTUNITY_HISTORY")

    def test_exact_one_minute_crosschecked_game_remains_eligible(self):
        local=[{"id":"123","team":"BOS","date":"2026-11-01","player":"Sample Player",
                "PTS":0,"REB":0,"AST":0,"MIN":1,"opponent":"NYK"}]
        source=[{"id":"123","team":"BOS","date":"2026-11-01","pts":0,"reb":0,
                 "ast":0,"minutes":1,"fga":0,"fta":0,"tov":0,"oreb":0}]
        rows,health=current_games(local,source)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["MIN"],1)
        self.assertEqual(health["MATCHED"],1)

    def test_conflicting_box_is_never_inferred(self):
        local=[{"id":"123","team":"BOS","date":"2026-11-01","player":"Sample Player",
                "PTS":20,"REB":5,"AST":4,"MIN":30,"opponent":"NYK"}]
        source=[{"id":"123","team":"BOS","date":"2026-11-01","pts":25,"reb":5,
                 "ast":4,"minutes":30,"fga":13,"fta":5,"tov":2,"oreb":1}]
        rows,health=current_games(local,source)
        self.assertEqual(rows,[])
        self.assertEqual(health["BOX_SCORE_DISAGREEMENT"],1)

    def test_insufficient_opponent_history_blocks_forecast(self):
        f,why=build_features([],"BOS","NYK","2026-11-09",{})
        self.assertIsNone(f)
        self.assertIsNotNone(why)

    def test_missing_opponent_context_neutral_fallback_is_explicit_and_prior_only(self):
        prior=[{"id":"123","player":"Example","team":"SAS","opponent":"CHI",
                "date":f"2026-11-{i:02d}","PTS":20.,"REB":5.,"AST":4.,
                "MIN":30.,"FGA":15.,"FTA":4.,"TOV":2.,"OREB":1.}
               for i in range(1,10)]
        blocked,reason=build_features(prior,"SAS","CHI","2026-11-12",{})
        self.assertIsNone(blocked)
        self.assertEqual(reason,"INSUFFICIENT_PRIOR_OPPONENT_PACE_DEFENSE")
        features,reason=build_features(prior,"SAS","CHI","2026-11-12",{},
                                       neutral_defense_on_missing=True)
        self.assertIsNone(reason)
        self.assertTrue(features["opponent_context_unavailable"])
        self.assertEqual(features["opponent_pace_factor"],1.0)
        self.assertEqual(features["opponent_defense_factor"],1.0)
        # Never learn from a row dated on or after the upcoming matchup.
        prior.append({**prior[-1],"date":"2026-11-12","PTS":80.})
        again,reason=build_features(prior,"SAS","CHI","2026-11-12",{},
                                    neutral_defense_on_missing=True)
        self.assertEqual(again["last10_points"],features["last10_points"])

    def test_only_standard_points_two_sided_line_selected(self):
        base={"player":"Jokić","team":"DEN","game":"Denver Nuggets @ Houston Rockets",
              "start":"2026-11-10T01:30:00Z","stat":"Points",
              "market_updated":"2026-11-09T21:00:00Z"}
        offers=[]
        for line,tier in ((23.5,"goblin"),(27.5,"standard"),(32.5,"demon")):
            for side in ("More","Less"):
                offers.append({**base,"line":line,"pickem_tier":tier,"direction":side})
        selected,excluded=standard_points_offers(offers)
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0]["line"],27.5)
        self.assertEqual(selected[0]["pickem_tier"],"standard")
        self.assertTrue(selected[0]["standard_line_two_sided_verified"])
        self.assertEqual(excluded["NON_STANDARD_POINTS_TIER"],4)

    def test_conflicting_standard_lines_fail_closed(self):
        base={"player":"Test","team":"DEN","game":"Denver Nuggets @ Houston Rockets",
              "start":"2026-11-10T01:30:00Z","stat":"Points",
              "market_updated":"2026-11-09T21:00:00Z","pickem_tier":"standard"}
        offered=[{**base,"line":line,"direction":side} for line in (23.5,24.5)
                 for side in ("More","Less")]
        selected,excluded=standard_points_offers(offered)
        self.assertEqual(selected,[])
        self.assertEqual(excluded["CONFLICTING_STANDARD_LINES"],4)

    def test_one_sided_standard_line_is_not_safely_verified(self):
        base={"player":"Test","team":"DEN","game":"Denver Nuggets @ Houston Rockets",
              "start":"2026-11-10T01:30:00Z","stat":"Points",
              "market_updated":"2026-11-09T21:00:00Z",
              "pickem_tier":"standard","line":24.5,"direction":"More"}
        selected,excluded=standard_points_offers([base])
        self.assertEqual(selected,[])
        self.assertEqual(excluded["INCOMPLETE_STANDARD_TWO_SIDED_LINE"],1)

    def test_stale_prizepicks_rejected(self):
        pack={"research_only":True,"production_modified":False,
              "columns":("minutes_forecast",),"training_seasons":("2022-23","2023-24"),
              "model":FakeModel()}
        offers={"source":"AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS","status":"STALE_PROVIDER_BOARD",
                "is_live":False,"updated_at":"2026-11-09T01:00:00Z","picks":[]}
        with self.assertRaises(ValueError):
            forecast([],offers,pack,now=datetime(2026,11,9,20,tzinfo=timezone.utc))

if __name__=="__main__":
    unittest.main()

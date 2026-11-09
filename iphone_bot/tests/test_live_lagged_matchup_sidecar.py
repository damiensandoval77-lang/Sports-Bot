"""Live challenger must reject stale lines and avoid invented projection confidence."""
from datetime import datetime,timezone
import unittest
try:
    from iphone_bot.live_lagged_matchup_sidecar import forecast,current_games,build_features
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

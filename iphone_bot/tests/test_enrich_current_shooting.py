import unittest
from datetime import date
from iphone_bot.enrich_current_shooting import overlay
def original():
    return {"id":"123","date":"2026-11-07","team":"BOS","opponent":"NYK",
      "PTS":17,"REB":6,"AST":3,"MIN":30,"FGA":12,"FG3A":5}
def source():
    return {"player_id":123,"game_date":"2026-11-07",
      "season":"2026-27","team":"BOS","opponent":"NYK","minutes":30,
      "pts":17,"reb":6,"ast":3,"fgm":6,"fga":12,"fg3m":2,"fg3a":5,
      "ftm":3,"fta":4}
class CurrentShootingEnrichmentTests(unittest.TestCase):
 def test_verified_identity_and_scoring_shot_makes(self):
    rows,health=overlay([original()],[source()],today=date(2026,11,8))
    self.assertEqual(health["matched_player_games"],1)
    self.assertEqual(rows[0]["FG3M"],2)
    self.assertEqual(rows[0]["FTA"],4)
    self.assertEqual(rows[0]["shooting_source"],
                     "CROSSCHECKED_HF_PLAYER_GAME_BOX_SCORE")
 def test_reject_inconsistent_or_future_box_scores(self):
    for bad in ({**source(),"pts":19},
                {**source(),"team":"NYK"},
                {**source(),"game_date":"2026-11-09"},
                {**source(),"fg3m":6},
                {**source(),"fga":14}):
        with self.subTest(bad=bad):
            rows,health=overlay([original()],[bad],today=date(2026,11,8))
            self.assertEqual(health["matched_player_games"],0)
            self.assertNotIn("FGM",rows[0])
 def test_target_game_cannot_be_used_as_future_feature(self):
    today=date(2026,11,8)
    rows,health=overlay([original(),{**original(),"date":"2026-11-09"}],
        [source(),{**source(),"game_date":"2026-11-09"}],today=today)
    self.assertEqual(health["matched_player_games"],1)
    self.assertNotIn("FGM",rows[1])
 def test_conflicting_duplicate_source_rows_are_discarded(self):
    first=source()
    conflicting={**source(),"fgm":7,"fg3m":2,"pts":19}
    rows,health=overlay([original()],[first,conflicting],today=date(2026,11,8))
    self.assertEqual(health["matched_player_games"],0)

"""NFL final boxscore integrity tests."""
import sys,unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from export_nfl_boxscores import build,prepare,validate_against_published
class TestNFLBoxscores(unittest.TestCase):
 def setup_data(self):
  schedule={"season":2026,"game_count":272,"games":[dict(
   game_id=f"g{i}",week=1,home="BUF",away="MIA",
   home_score=20 if i==0 else None,away_score=17 if i==0 else None,
   status="final" if i==0 else "scheduled") for i in range(272)]}
  rows=pd.DataFrame([
   dict(game_id="g0",player_id="qb",player_display_name="Quarterback",
        season=2026,season_type="REG",week=1,team="BUF",
        passing_yards=245),
   dict(game_id="g1",player_id="other",player_display_name="Future",
        season=2026,season_type="REG",week=1,team="BUF",
        passing_yards=400)])
  return schedule,rows
 def test_finals_only(self):
  s,r=self.setup_data()
  weeks,n=build(s,r)
  self.assertEqual(n,1)
  self.assertEqual(len(weeks[1]),1)
  self.assertEqual(weeks[1][0]["players"][0]["passing_yards"],245)
  self.assertIsNone(weeks[1][0]["players"][0]["receptions"])
 def test_missing_boxscore_is_pending(self):
  s,r=self.setup_data()
  s["games"][1].update(status="final",home_score=10,away_score=7)
  _,m=prepare(s,r[r.game_id.ne("g1")].copy())
  self.assertEqual(m["pending_boxscores"],1)
 def test_no_regression(self):
  s,r=self.setup_data()
  with self.assertRaisesRegex(ValueError,"Regressed game coverage"):
   prepare(s,r,{"game_ids":["g0","g2"]})
 def test_missing_player_name_blocks_export(self):
  sched,rows=self.setup_data()
  rows.loc[0,"player_display_name"]=None
  with self.assertRaisesRegex(ValueError,"Missing verified display name"):
   build(sched,rows)
 def test_blank_name_after_trim_blocks_export(self):
  sched,rows=self.setup_data()
  rows.loc[0,"player_display_name"]="   "
  with self.assertRaisesRegex(ValueError,"Missing verified display name"):
   build(sched,rows)
 def test_truncated_published_player_list_is_rejected(self):
  import tempfile,json
  with tempfile.TemporaryDirectory() as folder:
   out=Path(folder)
   old_players=[{"player":f"Player {n}","team":"BUF"} for n in range(12)]
   (out/"week_01.json").write_text(json.dumps({"season":2026,"week":1,
      "games":[{"game_id":"g0","players":old_players}]}))
   smaller={1:[{"game_id":"g0","players":[{"player":"Player 1","team":"BUF"}]}]}
   with self.assertRaisesRegex(ValueError,"truncated player boxscore"):
    validate_against_published(smaller,out)
 def test_valid_named_players_allowed(self):
  self.assertTrue(validate_against_published({1:[{"game_id":"g0","players":[{"player":"Quarterback","team":"BUF"}]}]},Path("/nonexistent-nfl-boxscore-test-directory")))
 def test_duplicate_and_wrong_team_fail(self):
  s,r=self.setup_data()
  with self.assertRaisesRegex(ValueError,"Duplicate"):
   build(s,pd.concat([r,r.iloc[[0]]]))
  r.loc[0,"team"]="NYJ"
  with self.assertRaisesRegex(ValueError,"does not match"):
   build(s,r)
if __name__=="__main__":unittest.main()

import copy,json,unittest
from pathlib import Path
from iphone_bot.grade_frozen_baseline_join import grade
SNAP=json.loads(Path("docs/frozen_baseline_pregame_lines_2026-11-09.json").read_text())
class FrozenBaselineTests(unittest.TestCase):
 def test_real_saved_pretip_snapshot_all_rows_valid_and_pending(self):
  out=grade(SNAP,{"version":1,"records":[]})
  self.assertEqual(out["total_original_records"],len(SNAP["records"]))
  self.assertEqual(out["pending"],len(SNAP["records"]))
  self.assertEqual(out["verified_final_grades"],0)
  self.assertTrue(out["not_betting_roi"])
 def test_verified_final_grades_exact_original_identity(self):
  r=SNAP["records"][0]
  f={k:r[k] for k in ("player_id","team","game","start","stat")}
  f.update({"status":"GRADED","actual":r["line"]+1,
    "final_source":"NBA_CDN_FINAL","source_game_id":"0022600001"})
  one={"status":SNAP["status"],"immutable_predictions":True,"records":[r]}
  out=grade(one,{"records":[f]})
  self.assertEqual(out["verified_final_grades"],1)
  self.assertIs(out["records"][0]["model_direction_hit"] is True or
                out["records"][0]["model_direction_hit"] is False,True)
 def test_wrong_team_fails_closed(self):
  r=SNAP["records"][0]
  f={k:r[k] for k in ("player_id","team","game","start","stat")}
  f.update({"status":"GRADED","actual":23,"final_source":"NBA_CDN_FINAL","source_game_id":"0022600001","team":"WRONG"})
  one={"status":SNAP["status"],"immutable_predictions":True,"records":[r]}
  self.assertEqual(grade(one,{"records":[f]})["pending"],1)
 def test_no_retroactive_frozen_or_provider_timestamp(self):
  x=copy.deepcopy(SNAP);x["records"][0]["locked_at"]=x["records"][0]["start"]
  with self.assertRaises(ValueError):grade(x,{"records":[]})
 def test_fake_source_not_a_grade(self):
  r=SNAP["records"][0]
  f={k:r[k] for k in ("player_id","team","game","start","stat")}
  f.update({"status":"GRADED","actual":12,"final_source":"FAKE","source_game_id":"1"})
  one={"status":SNAP["status"],"immutable_predictions":True,"records":[r]}
  self.assertEqual(grade(one,{"records":[f]})["pending"],1)
if __name__=="__main__":unittest.main()

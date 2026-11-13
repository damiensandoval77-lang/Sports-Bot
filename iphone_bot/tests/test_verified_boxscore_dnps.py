import copy
import json
import unittest
from pathlib import Path
from iphone_bot.verified_boxscore_dnps import verified_boxscore_dnp_rows, SOURCE

FIX=json.loads(Path("docs/verified_boxscore_dnps_2026-11-08.json").read_text())
def final_rows():
    return [
      {"source_game_id":"0022600202","date":"2026-11-08",
       "team":team,"opponent":opponent,"final_confirmed":True,
       "source":"NBA_CDN_FINAL","player":"An Observed Player"}
      for team,opponent in (("MIA","SAC"),("SAC","MIA"))
    ]
class DnpEvidenceTests(unittest.TestCase):
    def test_verified_five_players_no_zeros(self):
        rows=verified_boxscore_dnp_rows(final_rows(),FIX)
        self.assertEqual(len(rows),5)
        self.assertEqual({r["source"] for r in rows},{SOURCE})
        self.assertNotIn("Nique Clifford",{r["player"] for r in rows})
        self.assertTrue(all(r["PTS"] is None and r["MIN"] is None for r in rows))
    def test_no_verified_final_no_exclusion(self):
        self.assertEqual(verified_boxscore_dnp_rows([],FIX),[])
    def test_wrong_final_game_not_accepted(self):
        rows=final_rows()
        for r in rows:r["source_game_id"]="0022600199"
        self.assertEqual(verified_boxscore_dnp_rows(rows,FIX),[])
    def test_falsified_player_list_fails(self):
        fixture=copy.deepcopy(FIX)
        fixture["players"][0]["player"]="Nique Clifford"
        with self.assertRaises(ValueError):verified_boxscore_dnp_rows(final_rows(),fixture)
    def test_conflicting_played_stat_blocks_exclusion(self):
        rows=final_rows()
        rows.append({**rows[0],"player":"Dru Smith","MIN":10,"PTS":4})
        with self.assertRaises(ValueError):verified_boxscore_dnp_rows(rows,FIX)
    def test_missing_second_source_fails(self):
        fixture=copy.deepcopy(FIX)
        fixture["players"][0]["corroboration_url"]=fixture["players"][0]["primary_url"]
        with self.assertRaises(ValueError):verified_boxscore_dnp_rows(final_rows(),fixture)
    def test_wrong_date_fails(self):
        fixture=copy.deepcopy(FIX);fixture["date_eastern"]="2026-11-09"
        with self.assertRaises(ValueError):verified_boxscore_dnp_rows(final_rows(),fixture)
if __name__=="__main__":unittest.main()

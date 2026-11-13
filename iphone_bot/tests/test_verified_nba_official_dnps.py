import unittest
from iphone_bot.verified_nba_official_dnps import crosschecked_official_dnp,load_official_dnp

def rows():
    out=[]
    games=[("0022600207","IND","DAL"),("0022600208","DEN","HOU"),("0022600203","LAL","ATL")]
    for gid,a,h in games:
        for team,opp in ((a,h),(h,a)):
            for n in range(3):
                out.append({"source_game_id":gid,"team":team,"opponent":opp,
                    "player":f"Verified Player {n} {team}","date":"2026-11-09",
                    "source":"NBA_CDN_FINAL","final_confirmed":True,"PTS":10,"MIN":20})
    return out
class OfficialDnpEvidenceTests(unittest.TestCase):
    def test_matching_verified_final_games_recover_exact_sourced_dnps(self):
        result=load_official_dnp(rows())
        self.assertEqual(len(result),10)
        self.assertTrue(all(x["dnp_final_verified"] for x in result))
        self.assertEqual(len([x for x in result if x["team"]=="IND"]),2)
        self.assertEqual(len([x for x in result if x["team"]=="HOU"]),2)
    def test_missing_final_game_cannot_infer_dnp(self):
        result=load_official_dnp([])
        self.assertEqual(result,[])
    def test_conflicting_played_player_is_not_excluded(self):
        played={**rows()[0],"player":"Clint Capela","team":"HOU","opponent":"DEN","source_game_id":"0022600208"}
        result=load_official_dnp(rows()+[played])
        self.assertNotIn("Clint Capela",[x["player"] for x in result])
    def test_reject_unattributed_or_ambiguous_fixture(self):
        fixture={"status":"OFFICIAL_NBA_FINAL_EXPLICIT_DNP_CROSSCHECK",
                 "date_eastern":"2026-11-09","games":[{
                 "game_id":"0022600207","away":"IND","home":"DAL",
                 "source_url":"https://untrusted.example/0022600207",
                 "players":[{"player":"Jay Huff","team":"IND","reason":"DNP - Coach's Decision"}]}]}
        with self.assertRaises(ValueError):crosschecked_official_dnp(rows(),fixture)
if __name__=="__main__":unittest.main()

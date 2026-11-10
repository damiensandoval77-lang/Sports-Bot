import unittest
from iphone_bot.verified_nov9_nonparticipants import load_nonparticipants,nonparticipants,SOURCE
from iphone_bot.prizepicks_research_ledger import settle

def finals():
    groups={"0022600203":("LAL","ATL"),"0022600204":("CLE","CHA"),
      "0022600205":("WAS","DET"),"0022600206":("MEM","TOR"),
      "0022600207":("IND","DAL"),"0022600208":("DEN","HOU"),
      "0022600209":("SAS","PHX"),"0022600210":("NOP","GSW")}
    out=[]
    for gid,(away,home) in groups.items():
        for team,opponent in ((away,home),(home,away)):
            for i in range(3):
                out.append({"player":f"Playing Person {i} {team}",
                   "team":team,"opponent":opponent,"source_game_id":gid,
                   "date":"2026-11-09","source":"NBA_CDN_FINAL",
                   "final_confirmed":True,"PTS":10,"MIN":24})
    return out

class NonparticipantTests(unittest.TestCase):
    def test_verified_matchups_produce_sourced_nonparticipants(self):
        rows=load_nonparticipants(finals())
        self.assertEqual(len(rows),24)
        self.assertTrue(all(r["dnp_final_verified"] is True for r in rows))
        self.assertTrue(all(r["source"] in ("NBA_OFFICIAL_INACTIVE_CROSSCHECKED",SOURCE) for r in rows))
    def test_no_verified_final_never_produces_exclusions(self):
        self.assertEqual(load_nonparticipants([]),[])
    def test_contradictory_played_identity_remains_unresolved(self):
        rows=finals()+[{"player":"Scottie Barnes","team":"TOR","opponent":"MEM",
           "source_game_id":"0022600206","date":"2026-11-09","source":"NBA_CDN_FINAL",
           "final_confirmed":True,"PTS":25,"MIN":35}]
        self.assertNotIn("Scottie Barnes",[r["player"] for r in load_nonparticipants(rows)])
    def test_research_only_voids_and_cannot_count_missing_player_as_under(self):
        final=[x for x in load_nonparticipants(finals()) if x["player"]=="Scottie Barnes"]
        row={"status":"PENDING","start":"2026-11-10T00:30:00Z",
             "game":"Memphis Grizzlies @ Toronto Raptors","team":"TOR",
             "player":"Scottie Barnes","player_id":"p1","stat":"PTS",
             "line":19.5,"combined_projection":23}
        result=settle({"records":[row]},[],final_games=final)["records"][0]
        self.assertEqual(result["status"],"VOID_DNP")
        self.assertIsNone(result["actual"])
        self.assertEqual(result["settlement_source"],SOURCE)
        result=settle({"records":[row]},[],final_games=[])["records"][0]
        self.assertEqual(result["status"],"PENDING")
if __name__=="__main__":unittest.main()

"""Official NBA web-final manually corroborated fixture remains provenance-checked."""
import json
import tempfile
import unittest
from pathlib import Path
from iphone_bot.paper_pick_pipeline import official_web_cross_checked_final,settle

FIXTURE=Path(__file__).resolve().parents[2]/"docs/verified_spurs_kings_boxscores.json"
GAME="San Antonio Spurs @ Sacramento Kings"

class OfficialFinalTests(unittest.TestCase):
    def test_crosschecked_final_matches_13_saved_players(self):
        rows=official_web_cross_checked_final(FIXTURE)
        self.assertEqual(len(rows),13)
        self.assertEqual(next(x for x in rows if x["player"]=="Victor Wembanyama")["PRA"],46)
        self.assertEqual(next(x for x in rows if x["player"]=="Domantas Sabonis")["REB"],12)

    def test_rejects_score_or_identity_tamper(self):
        orig=json.loads(FIXTURE.read_text())
        for mutate in ("bad_total","bad_team","duplicate","bad_provenance"):
            data=json.loads(json.dumps(orig))
            if mutate=="bad_total":data["records"][0]["PRA"]+=10
            if mutate=="bad_team":data["records"][0]["team"]="BOS"
            if mutate=="duplicate":data["records"].append(dict(data["records"][0]))
            if mutate=="bad_provenance":data["source_url"]="https://untrusted.example/nba"
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/"bad.json"
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    official_web_cross_checked_final(path)

    def test_only_pregame_quote_is_graded(self):
        rows=official_web_cross_checked_final(FIXTURE)
        row={"status":"PENDING","event_start":"2026-11-07T03:10:00Z",
             "captured_at":"2026-11-07T01:05:00Z",
             "player_id":"1641705","player":"Victor Wembanyama","team":"SAS",
             "game":GAME,"market":"PTS","line":29.5,"side":"OVER",
             "american_odds":-110,"original_projection":31.5,"combined_projection":31.}
        done=settle([row],rows,now="2026-11-07T07:00:00Z")
        self.assertEqual(done[0]["actual"],30)
        self.assertEqual(done[0]["result"],"WIN")
        late={**row,"captured_at":"2026-11-07T03:11:00Z"}
        self.assertEqual(settle([late],rows,now="2026-11-07T07:00:00Z")[0]["status"],
                         "INVALID_LATE_CAPTURE")

if __name__=="__main__":unittest.main()

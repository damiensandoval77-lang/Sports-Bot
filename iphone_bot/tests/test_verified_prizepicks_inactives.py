"""No post-tip winner fabrication: verify exact November 8 official inactivity only."""
import json
import unittest
from pathlib import Path

from iphone_bot.verified_prizepicks_inactives import verified_inactive_rows, verified_inactive_subset, additional_verified_ai_inactive_subset, FIXTURE
from iphone_bot.prizepicks_research_ledger import settle

FIX=json.loads(FIXTURE.read_text())
NOW=__import__("datetime").datetime(2026,11,9,14,tzinfo=__import__("datetime").timezone.utc)

def final_game_headers():
    return [{
        "source_game_id":x["game_id"],"date":FIX["game_date_eastern"],
        "team":x["team"],"opponent":x["opponent"],
        "final_confirmed":True,"source":"NBA_CDN_FINAL",
        "player":"Independent Played Player"
    } for x in FIX["players"]]

def locked_record(x):
    team_names={"LAL":"Los Angeles Lakers @ Detroit Pistons",
                "SAC":"Miami Heat @ Sacramento Kings",
                "CHI":"Philadelphia 76ers @ Chicago Bulls",
                "UTA":"Utah Jazz @ Minnesota Timberwolves"}
    return {"status":"PENDING","player":x["player"],"player_id":"1234",
            "team":x["team"],"game":team_names[x["team"]],
            "start":"2026-11-09T00:00:00Z",
            "stat":"PTS","line":20.5,"combined_projection":23.7}

class VerifiedNov8InactiveTests(unittest.TestCase):
    def test_all_four_verified_official_inactives_match_final_game_ids(self):
        rows=verified_inactive_rows(final_game_headers(),FIX)
        self.assertEqual(len(rows),4)
        self.assertEqual({r["player"] for r in rows},
                         {"Luka Dončić","Domantas Sabonis","Norman Powell","Lauri Markkanen"})
        self.assertTrue(all(r["dnp_final_verified"] for r in rows))
        self.assertTrue(all(r["PTS"] is None for r in rows))

    def test_all_four_void_without_rewriting_lines_or_projections(self):
        rows=verified_inactive_rows(final_game_headers(),FIX)
        original=[locked_record(x) for x in FIX["players"]]
        graded=settle({"records":original},[],now=NOW,final_games=rows)["records"]
        self.assertEqual([g["status"] for g in graded],["VOID_DNP"]*4)
        self.assertEqual([g["result"] for g in graded],["VOID"]*4)
        self.assertEqual([g["line"] for g in graded],[20.5]*4)
        self.assertTrue(all(g["actual"] is None for g in graded))
        self.assertTrue(all(g["combined_projection"]==23.7 for g in graded))

    def test_partial_official_slate_confirms_only_that_games_inactive(self):
        # The AI archive includes UTA/MIN and MIA/SAC; not every fixture game.
        subset=[g for g in final_game_headers() if g["team"] in ("UTA","SAC")]
        rows=verified_inactive_subset(subset)
        self.assertEqual({r["player"] for r in rows},{"Lauri Markkanen","Domantas Sabonis"})
        self.assertTrue(all(r["source_game_id"] in {g["source_game_id"] for g in subset} for r in rows))

    def test_other_november_eight_ai_inactives_require_exact_final_games(self):
        headers=[
            {"source_game_id":"0022600199","date":"2026-11-08",
             "team":"BKN","opponent":"DAL","final_confirmed":True,
             "source":"NBA_CDN_FINAL","player":"Other Nets Player"},
            {"source_game_id":"0022600201","date":"2026-11-08",
             "team":"LAC","opponent":"NOP","final_confirmed":True,
             "source":"NBA_CDN_FINAL","player":"Other Clippers Player"}]
        rows=additional_verified_ai_inactive_subset(headers)
        self.assertEqual({r["player"] for r in rows},{"Mikel Brown Jr.","Isaiah Jackson"})
        self.assertEqual(additional_verified_ai_inactive_subset([]),[])
        self.assertTrue(all(r["PTS"] is None and r["dnp_final_verified"] for r in rows))

    def test_confirmed_played_cannot_be_excluded_from_other_ai_inactives(self):
        headers=[{"source_game_id":"0022600199","date":"2026-11-08",
                  "team":"BKN","opponent":"DAL","final_confirmed":True,
                  "source":"NBA_CDN_FINAL","player":"Mikel Brown Jr."}]
        with self.assertRaises(ValueError):
            additional_verified_ai_inactive_subset(headers)

    def test_does_not_void_if_verified_game_is_missing(self):
        with self.assertRaises(ValueError):
            verified_inactive_rows(final_game_headers()[:3],FIX)

    def test_does_not_void_a_confirmed_played_player(self):
        played=final_game_headers()
        played.append({**played[0],"player":"Luka Dončić"})
        with self.assertRaises(ValueError):
            verified_inactive_rows(played,FIX)

    def test_bad_sources_or_wrong_date_rejected(self):
        copy=json.loads(json.dumps(FIX))
        copy["game_date_eastern"]="2026-11-09"
        with self.assertRaises(ValueError):
            verified_inactive_rows(final_game_headers(),copy)
        copy=json.loads(json.dumps(FIX))
        copy["players"][0]["official_inactive_url"]="https://example.com/game/fake"
        with self.assertRaises(ValueError):
            verified_inactive_rows(final_game_headers(),copy)

    def test_manual_inactive_source_can_never_grade_played_stats(self):
        rows=verified_inactive_rows(final_game_headers(),FIX)
        fake={**rows[0],"dnp_final_verified":False,
              "PTS":35,"REB":5,"AST":5,"PRA":45,"MIN":32}
        outcome=settle({"records":[locked_record(FIX["players"][0])]},[],now=NOW,
                       final_games=[fake])["records"][0]
        self.assertEqual(outcome["status"],"PENDING")

if __name__=="__main__":
    unittest.main()

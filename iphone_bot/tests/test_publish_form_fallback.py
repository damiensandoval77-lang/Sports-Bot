"""Verify real odds pairing, player-game matching, and no fake AI certainty."""
import datetime as dt
import unittest
from iphone_bot.publish_form_fallback import build,baseline


def player(name="Test Player",team="DAL",pid="1",games=9):
    vals={"l5":20.0,"l10":18.0,"season":17.0}
    return {"player":name,"team":team,"player_id":pid,"games":games,
            "latest_game":"2026-11-05","metrics":{stat:dict(vals)
            for stat in ("PTS","REB","AST","PRA")}}


def fixtures():
    time="2026-11-07T03:10:00Z"
    game="Utah Jazz @ Dallas Mavericks"
    quotes=[{"game":game,"start":time,"player":"Test Player",
             "stat":"Points","direction":side,"odds":-110,
             "line":19.5,"source":"Book A"} for side in ("More","Less")]
    f={"season":"2026-27","updated_at":"2026-11-07T00:00:00Z",
       "players":[player()]}
    o={"source":"THE_ODDS_API_VERIFIED_COMPACT_PLAYER_PROPS",
       "updated_at":"2026-11-07T00:00:00Z","is_live":True,"picks":quotes}
    now=dt.datetime(2026,11,7,0,30,tzinfo=dt.timezone.utc)
    return f,o,now


class FormFallbackTests(unittest.TestCase):
    def test_prior_form_blend_and_not_trained_ai(self):
        f,o,now=fixtures()
        result=build(f,o,now)
        self.assertEqual(result["games_with_fallback"],1)
        self.assertEqual(result["comparison_rows_published"],1)
        row=result["comparisons"][0]
        self.assertEqual(row["projection"],round(.5*20+.3*18+.2*17,2))
        self.assertEqual(row["line"],19.5)
        self.assertFalse(result["is_trained_ai"])
        self.assertIsNone(row["estimated_selected_probability"])
        self.assertTrue(row["requires_lineup_review"])

    def test_requires_two_sided_quotes_and_team_match(self):
        f,o,now=fixtures()
        o["picks"]=o["picks"][:1]
        self.assertFalse(build(f,o,now)["comparisons"])
        f,o,now=fixtures()
        f["players"][0]["team"]="NYK"
        self.assertFalse(build(f,o,now)["comparisons"])

    def test_stale_form_and_quotes_fail(self):
        f,o,now=fixtures()
        o["updated_at"]="2026-11-04T00:00:00Z"
        with self.assertRaises(ValueError):build(f,o,now)

    def test_minimum_game_history_is_required(self):
        self.assertIsNone(baseline(player(games=4),"PTS"))

    def test_mixed_games_produce_distinct_matchups(self):
        f,o,now=fixtures()
        f["players"].append(player("Other Player","MEM","2"))
        for side in ("More","Less"):
            o["picks"].append({"game":"Oklahoma City Thunder @ Memphis Grizzlies",
                "start":"2026-11-07T02:10:00Z","player":"Other Player",
                "stat":"Assists","direction":side,"odds":-115,
                "line":5.5,"source":"Book A"})
        r=build(f,o,now)
        self.assertEqual(r["games_with_fallback"],2)
        self.assertEqual(len(r["comparisons"]),2)


if __name__=="__main__":unittest.main()

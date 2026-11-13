"""Regression tests for fully observed ESPN injury-list DNP policy."""
import datetime as dt
import unittest
from iphone_bot.espn_injury_void import decide,facts,run

GAME="Miami Heat @ Utah Jazz"
REC={"player_id":"1","player":"Lauri Markkanen","team":"UTA","game":GAME,
     "start":"2026-11-11T02:00:00+00:00","stat":"PTS","grade":"PENDING","projection":20.0}
def summary(final=True,listed=True,played=False,teams=2):
    comps=[{"homeAway":"away","team":{"displayName":"Miami Heat"}},
           {"homeAway":"home","team":{"displayName":"Utah Jazz"}}]
    rows=[{"athlete":{"displayName":"Lauri Markkanen" if played else "Someone Else"},
           "stats":["20","4"]}]
    return {"header":{"competitions":[{"status":{"type":{"completed":final}},"competitors":comps}]},
            "boxscore":{"players":[{"statistics":[{"athletes":rows}]} for _ in range(teams)]},
            "injuries":[{"injuries":[{"athlete":{"displayName":"Lauri Markkanen"},"status":"Out"}] if listed else []}]}
def evidence(**kw):return facts(summary(**kw),"game-id")
class VoidPolicy(unittest.TestCase):
    def test_absent_injured_final(self):
        r=decide(REC,evidence())
        self.assertEqual(r["status"],"EXCLUDED_VERIFIED_DNP")
        self.assertIsNone(r["actual"])
    def test_player_with_stats_is_not_void(self):self.assertIsNone(decide(REC,evidence(played=True)))
    def test_unlisted_is_not_void(self):self.assertIsNone(decide(REC,evidence(listed=False)))
    def test_unfinished_is_not_void(self):self.assertIsNone(decide(REC,evidence(final=False)))
    def test_incomplete_is_not_void(self):self.assertIsNone(decide(REC,evidence(teams=1)))
    def test_different_matchup_is_not_void(self):
        self.assertIsNone(decide({**REC,"game":"Bulls @ Jazz"},evidence()))
    def test_idempotent(self):
        board={"events":[{"id":"game-id","competitions":[{"competitors":summary()["header"]["competitions"][0]["competitors"]}]}]}
        reader=lambda url:board if "scoreboard" in url else summary()
        now=dt.datetime(2026,11,11,22,tzinfo=dt.timezone.utc)
        first=run([REC],[],now,reader)
        self.assertEqual(len(first),1)
        self.assertEqual(run([REC],first,now,reader),[])
    def test_no_early_game_void(self):
        now=dt.datetime(2026,11,11,22,tzinfo=dt.timezone.utc)
        self.assertEqual(run([{**REC,"start":"2026-11-11T20:00:00+00:00"}],[],now,lambda _:None),[])
if __name__=="__main__":unittest.main()

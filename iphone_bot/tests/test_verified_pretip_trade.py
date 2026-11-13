import copy,json,unittest
from pathlib import Path
from iphone_bot.verified_pretip_trade import verified_trade_rows,SOURCE
from iphone_bot.grade_frozen_ai_forecasts import settle_predictions,report

F=json.loads(Path("docs/verified_pretip_trade_2026-11-08.json").read_text())
GAME={"source_game_id":"0022600202","date":"2026-11-08","team":"SAC",
      "opponent":"MIA","final_confirmed":True,"source":"NBA_CDN_FINAL","player":"Alex Karaban"}
class PretipTradeTests(unittest.TestCase):
    def test_grader_records_verified_trade_exclusion_without_fake_stats(self):
        p={"player_id":"1642363","player":"Nique Clifford","team":"SAC",
           "game":"Miami Heat @ Sacramento Kings","start":"2026-11-09T02:00:00+00:00",
           "stat":"PTS","projection":6.4,"captured_at":"2026-11-08T19:00:00+00:00"}
        transfers=verified_trade_rows([GAME],F)
        result=settle_predictions([p],[GAME],confirmed_transfers=transfers)
        self.assertEqual(result["new_transfers"],1)
        self.assertEqual(result["records"][0]["status"],"EXCLUDED_VERIFIED_NONPARTICIPANT")
        self.assertIsNone(result["records"][0]["actual"])
        import datetime as dt
        audit=report("2026-11-08",[p],result,now=dt.datetime(2026,11,10,tzinfo=dt.timezone.utc))
        self.assertEqual(audit["ungraded"],0)
        self.assertEqual(audit["verified_dnp_exclusions"],0)
        self.assertEqual(audit["verified_pretip_transfer_exclusions"],1)
        self.assertEqual(audit["accounted_for"],1)
    def test_unverified_transfer_does_not_change_grades(self):
        p={"player_id":"1642363","player":"Nique Clifford","team":"SAC",
           "game":"Miami Heat @ Sacramento Kings","start":"2026-11-09T02:00:00+00:00",
           "stat":"PTS","projection":6.4,"captured_at":"2026-11-08T19:00:00+00:00"}
        self.assertEqual(settle_predictions([p],[GAME])["records"],[])
    def test_verified_roster_change(self):
        rows=verified_trade_rows([GAME],F)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["source"],SOURCE)
        self.assertEqual(rows[0]["player"],"Nique Clifford")
        self.assertNotIn("PTS",rows[0])
    def test_unverified_game_does_not_exclude(self):
        self.assertEqual(verified_trade_rows([] ,F),[])
    def test_after_tip_trade_rejected(self):
        f=copy.deepcopy(F)
        f["trade_announced_at"]="2026-11-08T19:00:00-08:00"
        with self.assertRaises(ValueError):verified_trade_rows([GAME],f)
    def test_conflicting_played_player_rejected(self):
        with self.assertRaises(ValueError):
            verified_trade_rows([GAME,{**GAME,"player":"Nique Clifford","MIN":10}],F)
    def test_wrong_trade_link_rejected(self):
        f=copy.deepcopy(F);f["original_team_release"]="https://example.com"
        with self.assertRaises(ValueError):verified_trade_rows([GAME],f)
    def test_wrong_game_identity_does_not_exclude(self):
        self.assertEqual(verified_trade_rows([{**GAME,"source_game_id":"0022600203"}],F),[])
if __name__=="__main__":unittest.main()

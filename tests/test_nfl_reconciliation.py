"""No-network regression coverage for NFL postgame reconciliation."""
import sys
import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from reconcile_nfl_boxscores import reconcile,read_and_audit

class TestNFLPostgameReconciliation(unittest.TestCase):
    def fixtures(self,box_present=True):
        now=datetime(2026,11,9,19,0,tzinfo=timezone.utc)
        games=[]
        for idx in range(272):
            finished=idx in (0,1)
            games.append({"game_id":f"g{idx}","season":2026,"week":1,
                          "home":"BUF","away":"MIA",
                          "home_score":24 if finished else None,
                          "away_score":17 if finished else None,
                          "status":"final" if finished else "scheduled",
                          "kickoff_utc":(now-timedelta(hours=20)).isoformat()})
        players=[{"player_id":"p1","player":"Example QB","team":"BUF",
                  "attempts":30,"passing_yards":240,"carries":2,
                  "rushing_yards":4,"targets":0,"receptions":0,"receiving_yards":0},
                 {"player_id":"p2","player":"Example WR","team":"MIA",
                  "attempts":0,"passing_yards":0,"carries":0,
                  "rushing_yards":0,"targets":7,"receptions":5,"receiving_yards":60}]
        box={"game_id":"g0","week":1,"home":"BUF","away":"MIA",
             "home_score":24,"away_score":17,"players":players}
        week={1:{"season":2026,"week":1,"games":[box]}} if box_present else {}
        manifest={"game_ids":["g0"]} if box_present else {"game_ids":[]}
        return {"season":2026,"games":games},manifest,week,now
    def test_missing_final_is_pending_not_zero(self):
        schedule,manifest,weeks,now=self.fixtures()
        report=reconcile(schedule,manifest,weeks,now)
        self.assertEqual(report["final_games"],2)
        self.assertEqual(report["verified_games"],1)
        self.assertEqual(report["pending_games"],1)
        self.assertEqual(report["overdue_games"],1)
        self.assertEqual(report["games_to_retry"][0]["game_id"],"g1")
        self.assertEqual(report["games_to_retry"][0]["reason"],"missing_boxscore")
    def test_score_mismatch_is_flagged(self):
        schedule,manifest,weeks,now=self.fixtures()
        weeks[1]["games"][0]["home_score"]=21
        report=reconcile(schedule,manifest,weeks,now)
        self.assertEqual(report["pending_games"],2)
        self.assertEqual(report["games_to_retry"][0]["reason"],"score_mismatch")
    def test_missing_name_and_wrong_team(self):
        schedule,manifest,weeks,now=self.fixtures()
        weeks[1]["games"][0]["players"][0]["player"]=" "
        report=reconcile(schedule,manifest,weeks,now)
        self.assertEqual(report["games_to_retry"][0]["reason"],"missing_player_name")
        weeks[1]["games"][0]["players"][0]["player"]="Example QB"
        weeks[1]["games"][0]["players"][0]["team"]="ATL"
        report=reconcile(schedule,manifest,weeks,now)
        self.assertEqual(report["games_to_retry"][0]["reason"],"wrong_player_team")
    def test_no_false_alert_while_game_not_final(self):
        schedule,manifest,weeks,now=self.fixtures()
        schedule["games"][1]["status"]="started_unconfirmed"
        schedule["games"][1]["home_score"]=None
        schedule["games"][1]["away_score"]=None
        report=reconcile(schedule,manifest,weeks,now)
        self.assertEqual(report["final_games"],1)
        self.assertEqual(report["pending_games"],0)
    def test_duplicate_games_and_bad_manifest_fail_closed(self):
        schedule,manifest,weeks,now=self.fixtures()
        weeks[2]={"season":2026,"week":2,"games":[weeks[1]["games"][0]]}
        with self.assertRaisesRegex(ValueError,"Duplicate game"):
            reconcile(schedule,manifest,weeks,now)
        weeks.pop(2)
        with self.assertRaisesRegex(ValueError,"Manifest game IDs"):
            reconcile(schedule,{"game_ids":["g9"]},weeks,now)
    def test_idempotent_audit_does_not_rewrite_file(self):
        schedule,manifest,weeks,now=self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"schedule.json").write_text(json.dumps(schedule))
            out=root/"boxscores"
            out.mkdir()
            (out/"manifest.json").write_text(json.dumps(manifest))
            (out/"week_01.json").write_text(json.dumps(weeks[1]))
            health=out/"health.json"
            a=read_and_audit(root/"schedule.json",out,health,now)
            original=health.read_bytes()
            b=read_and_audit(root/"schedule.json",out,health,now)
            self.assertEqual(original,health.read_bytes())
            self.assertEqual(a,b)
if __name__=="__main__":unittest.main()

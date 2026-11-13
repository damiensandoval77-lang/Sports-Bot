"""Public NFL prediction tracking must be repeatable and never retroactive."""
import csv
import json
import sys
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from reconcile_nfl_picks import (
    collect_history,closing,grade_finals,read_published_snapshot,read_csv,verified_boxscores,verified_inactives,verified_zero_snaps,verified_full_game_scoring,exact_fantasy_score,run)

def schedule():
    kickoff="2026-11-15T18:00:00+00:00"
    return {"g1":{"game_id":"g1","week":10,"status":"final",
                  "kickoff_utc":kickoff,"home":"BUF","away":"MIA",
                  "home_score":24,"away_score":17},
            "g2":{"game_id":"g2","week":10,"status":"scheduled",
                  "kickoff_utc":"2026-11-22T18:00:00+00:00",
                  "home":"GB","away":"CHI","home_score":None,"away_score":None}}
def bet(target="REC_YDS",line="55.5",captured="2026-11-14T17:00:00+00:00",
        odds="standard"):
    return {"captured_at":captured,"season":"2026","week":"10","game_id":"g1",
            "player_id":"gsis-1","player":"Example WR","team":"MIA",
            "opponent":"BUF","position":"WR","stat":"Receiving Yards",
            "target":target,"line":line,"odds_type":odds,"proj":"60.0",
            "pick":"More","model_pct":"58.0"}
def box():
    return {"g1":{"gsis-1":{"player":"Example WR","team":"MIA",
             "player_id":"gsis-1","receiving_yards":65,
             "receptions":5,"targets":8,"rushing_yards":0,
             "rushing_tds":0,"receiving_tds":1}}}

class PublicNFLGradeTests(unittest.TestCase):
    def test_real_bills_vikings_final_has_gradeable_archived_picks(self):
        # Regression: 2026 Nov 9 game is final, 1,374 pretip lines saved;
        # a stale health file said 0 graded and 0 pending despite a verified box.
        root=Path(__file__).resolve().parents[1]/"docs"/"nfl"/"data"
        schedule_data=json.loads((root/"schedule_2026.json").read_text())
        games={g["game_id"]:g for g in schedule_data["games"]}
        gid="2026_09_BUF_MIN"
        self.assertEqual(games[gid]["status"],"final")
        history=read_csv(root/"frozen_pick_history_2026.csv")
        frozen=[r for r in history if r["game_id"]==gid]
        self.assertGreater(len(frozen),0,"Saved pretip BUF-MIN lines were lost")
        boxscores,issues=verified_boxscores(games,root/"boxscores")
        self.assertNotIn(gid,issues)
        self.assertIn(gid,boxscores,"Final BUF-MIN player boxscore missing")
        grades,pending,candidates=grade_finals(frozen,games,boxscores,issues)
        self.assertGreater(candidates,0,"Final game with frozen picks incorrectly reported no grading candidates")
        self.assertGreater(len(grades),0,"Final verified player stats produced no grades")
        self.assertEqual(candidates,len(grades)+len(pending))
        self.assertTrue(all(g["grade_status"]=="graded" for g in grades))
    def test_exact_prizepicks_full_ppr_for_verified_bills_vikings(self):
        root=Path(__file__).resolve().parents[1]/"docs"/"nfl"/"data"
        schedule_data=json.loads((root/"schedule_2026.json").read_text())
        games={g["game_id"]:g for g in schedule_data["games"]}
        boxes,problems=verified_boxscores(games,root/"boxscores")
        full=verified_full_game_scoring(root)
        gid="2026_09_BUF_MIN"
        self.assertEqual(len(full[gid]["verified_game_scoring"]["touchdowns"]),2)
        self.assertAlmostEqual(exact_fantasy_score(boxes[gid]["00-0034857"],full[gid]),13.86)
        self.assertAlmostEqual(exact_fantasy_score(boxes[gid]["00-0037248"],full[gid]),16.7)
        frozen=[r for r in read_csv(root/"frozen_pick_history_2026.csv") if r["game_id"]==gid]
        graded,pending,expected=grade_finals(frozen,games,boxes,problems,
              verified_inactives(root),verified_zero_snaps(root),full)
        self.assertEqual(expected,len(graded)+len(pending))
        self.assertFalse(any(r["target"]=="FPTS" for r in pending))
        self.assertEqual(sum(r["target"]=="FPTS" for r in graded),33)
        self.assertEqual(sum(r["target"]=="ANY_TD" and r["player"] in
            ("Tai Felton","Ben Yurosek") for r in graded),2)
        self.assertEqual(len(pending),0)
        self.assertEqual(sum(r["target"]=="ANY_TD" and r["player"] in
            ("Tai Felton","Ben Yurosek","Gavin Bartholomew") for r in graded),3)
        # Participation evidence is mandatory: removing Gavin's verified
        # snap returns precisely one unsettled TD rather than a false loss.
        snaps=verified_zero_snaps(root)
        snaps.remove(("2026_09_BUF_MIN","00-0040215"))
        grades_without,pending_without,_=grade_finals(frozen,games,boxes,problems,
             verified_inactives(root),snaps,full)
        self.assertEqual(len(pending_without),1)
        self.assertEqual(pending_without[0]["player"],"Gavin Bartholomew")

    def test_fantasy_scoring_rejects_unverified_extra_td_and_missing_game(self):
        root=Path(__file__).resolve().parents[1]/"docs"/"nfl"/"data"
        scoring=verified_full_game_scoring(root)["2026_09_BUF_MIN"]
        player={"player_id":"00-0037248","team":"BUF","passing_yards":0,
          "passing_tds":0,"passing_interceptions":0,"rushing_yards":107,
          "rushing_tds":1,"receptions":0,"receiving_yards":0,"receiving_tds":0}
        self.assertAlmostEqual(exact_fantasy_score(player,scoring),16.7)
        self.assertIsNone(exact_fantasy_score(player,None))
        self.assertIsNone(exact_fantasy_score({**player,"receiving_tds":1},scoring))
        self.assertIsNone(exact_fantasy_score({**player,"passing_yards":None},scoring))

    def test_exact_evidence_survives_repeat_and_source_rotation(self):
        original=bet(); original.update(p_more="0.58",p_less="0.32",p_push="0.10",
                                       matchup_evidence='{"original":"bytes"}')
        rows,_=collect_history([bet()],[original],schedule())
        for field in ("p_more","p_less","p_push","matchup_evidence"):
            self.assertEqual(rows[0][field],original[field])
        repeated,_=collect_history(rows,[bet()],schedule())
        self.assertEqual(repeated,rows)
        rotated,_=collect_history(rows,[],schedule())
        self.assertEqual(rotated,rows)
        grades,_,_=grade_finals(rows,schedule(),box(),set())
        self.assertEqual(grades[0]["matchup_evidence"],original["matchup_evidence"])

    def test_conflicting_forecast_or_evidence_cannot_recertify_archive(self):
        original=bet();original.update(p_more="0.58",matchup_evidence='{"original":true}')
        for patch in ({"proj":"99"},{"p_more":"0.9"},{"matchup_evidence":"{}"}):
            with self.assertRaisesRegex(ValueError,"NFL_FROZEN_"):
                collect_history([original],[{**original,**patch}],schedule())
        late={**original,"captured_at":"2026-11-15T18:00:00+00:00"}
        rows,rejected=collect_history([original],[late],schedule())
        self.assertEqual(len(rows),1);self.assertEqual(rejected,1)
        self.assertEqual(rows[0]["matchup_evidence"],original["matchup_evidence"])

    def test_only_pregame_captures_are_archived(self):
        old=bet()
        late=bet(captured="2026-11-16T17:00:00+00:00")
        hist,rejected=collect_history([], [old,late],schedule())
        self.assertEqual(len(hist),1)
        self.assertEqual(rejected,1)
    def test_last_standard_price_and_separate_alternatives(self):
        items=[bet(line="51.5"),bet(line="55.5",captured="2026-11-14T18:00:00+00:00"),
               bet(line="30.5",odds="goblin"),bet(line="90.5",odds="demon")]
        hist,_=collect_history([],items,schedule())
        choices=closing(hist,{"g1"})
        self.assertEqual(len(choices),3)
        self.assertEqual([c["line"] for c in choices if c["odds_type"]=="standard"],["55.5"])
    def test_verified_grades_push_and_missing_player_pending(self):
        hist,_=collect_history([],[bet(),bet(target="REC",line="5.0"),
            bet(target="TGT",line="6.5")],schedule())
        grades,pending,n=grade_finals(hist,schedule(),box(),set())
        self.assertEqual(n,3)
        self.assertEqual(len(grades),3)
        by_target={r["target"]:r for r in grades}
        self.assertEqual(by_target["REC_YDS"]["won"],"1")
        self.assertEqual(by_target["REC"]["result"],"Push")
        self.assertEqual(by_target["REC"]["won"],"")
        self.assertEqual(by_target["TGT"]["actual"],"8")
    def test_verified_inactive_voids_instead_of_incorrect_losses(self):
        inactive=bet(target="REC",line="0.5")
        hist,_=collect_history([],[inactive],schedule())
        grades,pending,n=grade_finals(hist,schedule(),{"g1":{}},set(),{("g1","gsis-1")})
        self.assertEqual((n,len(grades),len(pending)),(1,1,0))
        self.assertEqual(grades[0]["result"],"Void")
        self.assertEqual(grades[0]["won"],"")
        self.assertEqual(grades[0]["grade_status"],"void_verified_inactive")
        # Absence of a row without independent inactive evidence is never 0.
        grades,pending,_=grade_finals(hist,schedule(),{"g1":{}},set())
        self.assertEqual(len(grades),0)
        self.assertEqual(pending[0]["grade_status"],"player_not_in_verified_boxscore")
        # Contradictory official data must stop publication, not choose a side.
        with self.assertRaisesRegex(ValueError,"inactive has offensive boxscore"):
            grade_finals(hist,schedule(),box(),set(),{("g1","gsis-1")})

    def test_inactive_verification_requires_source_and_exact_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"verified_inactives_2026.json"
            p.write_text(json.dumps({"season":2026,"inactives":[
                {"game_id":"g1","player_id":"gsis-1","player":"Example WR",
                 "source_url":"https://example.com/source",
                 "published_at":"2026-11-15T12:00:00+00:00"}]}))
            self.assertEqual(verified_inactives(folder),{("g1","gsis-1")})
            p.write_text(json.dumps({"season":2026,"inactives":[
                {"game_id":"g1","player_id":"gsis-1"}]}))
            with self.assertRaisesRegex(ValueError,"Unattributed NFL inactive"):
                verified_inactives(folder)

    def test_participating_zero_target_player_grades_only_receiving(self):
        hist,_=collect_history([],[bet(target="REC",line="0.5"),
            bet(target="REC_YDS",line="4.5"),bet(target="ANY_TD",line="0.5"),
            bet(target="FPTS",line="5.5")],schedule())
        grades,pending,n=grade_finals(hist,schedule(),{"g1":{}},set(),
                                     zero_snaps={("g1","gsis-1")})
        self.assertEqual(n,4)
        self.assertEqual(len(grades),2)
        self.assertEqual(len(pending),2)
        self.assertTrue(all(row["actual"]=="0" and row["result"]=="Less" for row in grades))
        self.assertEqual({row["target"] for row in pending},{"ANY_TD","FPTS"})
        # A missing row alone is still not evidence of zero.
        grades,pending,_=grade_finals(hist,schedule(),{"g1":{}},set())
        self.assertEqual(len(grades),0)
        self.assertEqual(len(pending),4)

    def test_unsupported_market_cannot_be_scored(self):
        hist,_=collect_history([],[bet(target="FPTS")],schedule())
        grades,pending,_=grade_finals(hist,schedule(),box(),set())
        self.assertFalse(grades)
        self.assertEqual(pending[0]["grade_status"],"unsupported_exact_fantasy_scoring")
        missing,why,_=grade_finals(hist,schedule(),{},set())
        self.assertEqual(why[0]["grade_status"],"boxscore_not_yet_published")
    def test_repeat_archive_and_grading_are_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            all_games=[dict(game_id=f"g{i+100}",week=10,status="scheduled",
                  kickoff_utc="2026-11-22T18:00:00+00:00",
                  home="BUF",away="MIA",home_score=None,away_score=None)
                  for i in range(272)]
            all_games[0]=schedule()["g1"]
            (root/"schedule_2026.json").write_text(json.dumps(
                {"season":2026,"game_count":272,"games":all_games}))
            (root/"latest_2026_00.csv").write_text(
                ",".join(bet().keys())+"\n"+
                ",".join(bet().values())+"\n")
            (root/"latest_2026.json").write_text(json.dumps(
                {"season":2026,"captured_at":bet()["captured_at"],
                 "rows":1,"files":["latest_2026_00.csv"]}))
            boxes=root/"boxscores"
            boxes.mkdir()
            (boxes/"manifest.json").write_text(json.dumps({"season":2026,"game_ids":["g1"]}))
            (boxes/"week_10.json").write_text(json.dumps({"season":2026,"week":10,
               "games":[{"game_id":"g1","week":10,"home":"BUF","away":"MIA",
               "home_score":24,"away_score":17,
               "players":[box()["g1"]["gsis-1"]]}]}))
            result=run(root)
            self.assertEqual(result["graded_picks"],1)
            first=(root/"pp_graded_2026.csv").read_bytes()
            second=run(root)
            self.assertEqual(first,(root/"pp_graded_2026.csv").read_bytes())
            self.assertEqual(result,second)
    def test_full_postgame_transition_and_repeated_grading(self):
        # A valid pre-kickoff quote should be saved while the game is scheduled,
        # become pending once final, then settle from a verified player box score.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            all_games=[dict(game_id=f"dummy{i}",week=10,status="scheduled",
                kickoff_utc="2026-11-22T18:00:00+00:00",home="BUF",
                away="MIA",home_score=None,away_score=None)
                for i in range(271)]
            target=dict(schedule()["g1"],status="scheduled",
                home_score=None,away_score=None)
            def save_schedule():
                (root/"schedule_2026.json").write_text(json.dumps({
                    "season":2026,"game_count":272,"games":[target]+all_games}))
            save_schedule()
            record=bet()
            with (root/"latest_2026_00.csv").open("w",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=list(record))
                writer.writeheader();writer.writerow(record)
            (root/"latest_2026.json").write_text(json.dumps({
                "season":2026,"captured_at":record["captured_at"],
                "rows":1,"files":["latest_2026_00.csv"]}))
            boxroot=root/"boxscores"
            boxroot.mkdir()
            (boxroot/"manifest.json").write_text(json.dumps({
                "season":2026,"game_ids":[]}))
            before=run(root)
            self.assertEqual(before["archived_pregame_lines"],1)
            self.assertEqual(before["expected_final_picks"],0)
            self.assertEqual(before["graded_picks"],0)
            # Verified final score arrives first, but player stats lag.
            target.update(status="final",home_score=24,away_score=17)
            save_schedule()
            waiting=run(root)
            self.assertEqual(waiting["expected_final_picks"],1)
            self.assertEqual(waiting["pending_picks"],1)
            with (root/"pp_grading_pending_2026.csv").open(newline="") as handle:
                pending=list(csv.DictReader(handle))
            self.assertEqual(pending[0]["grade_status"],
                             "boxscore_not_yet_published")
            # Verified matching player boxscore arrives later.
            (boxroot/"manifest.json").write_text(json.dumps({
                "season":2026,"game_ids":["g1"]}))
            (boxroot/"week_10.json").write_text(json.dumps({
                "season":2026,"week":10,"games":[{
                    "game_id":"g1","week":10,"home":"BUF","away":"MIA",
                    "home_score":24,"away_score":17,
                    "players":[box()["g1"]["gsis-1"]]}]}))
            done=run(root)
            self.assertEqual(done["graded_picks"],1)
            self.assertEqual(done["pending_picks"],0)
            self.assertEqual(done["standard_settled"],1)
            self.assertEqual(done["standard_wins"],1)
            grade_bytes=(root/"pp_graded_2026.csv").read_bytes()
            archive_bytes=(root/"frozen_pick_history_2026.csv").read_bytes()
            self.assertEqual(run(root),done)
            self.assertEqual((root/"pp_graded_2026.csv").read_bytes(),grade_bytes)
            self.assertEqual((root/"frozen_pick_history_2026.csv").read_bytes(),
                             archive_bytes)
    def test_previous_published_archive_count_cannot_silently_disappear(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            games=[dict(game_id=f"dummy{i}",week=10,status="scheduled",
                        kickoff_utc="2026-11-22T18:00:00+00:00",
                        home="BUF",away="MIA",home_score=None,away_score=None)
                   for i in range(272)]
            (root/"schedule_2026.json").write_text(json.dumps(
                {"season":2026,"game_count":272,"games":games}))
            (root/"grading_health_2026.json").write_text(json.dumps(
                {"archived_pregame_lines":15}))
            # A broken CSV or missing export cannot replace 15 archived
            # captures with an empty, falsely healthy zero-grade report.
            with self.assertRaisesRegex(ValueError,"NFL_FROZEN_ARCHIVE_REGRESSION"):
                run(root)
            self.assertEqual(json.loads((root/"grading_health_2026.json").read_text())
                             ["archived_pregame_lines"],15)
            self.assertFalse((root/"pp_graded_2026.csv").exists())
    def test_prior_archived_history_cannot_be_dropped_after_schedule_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            games=[dict(game_id=f"dummy{i}",week=10,status="scheduled",
                        kickoff_utc="2026-11-22T18:00:00+00:00",
                        home="BUF",away="MIA",home_score=None,away_score=None)
                   for i in range(272)]
            (root/"schedule_2026.json").write_text(json.dumps(
                {"season":2026,"game_count":272,"games":games}))
            with (root/"frozen_pick_history_2026.csv").open("w",newline="") as fh:
                writer=csv.DictWriter(fh,fieldnames=list(bet()))
                writer.writeheader();writer.writerow(bet())
            with self.assertRaisesRegex(ValueError,"NFL_FROZEN_ARCHIVE_REGRESSION"):
                run(root)
    def test_invalid_public_snapshot_does_not_wipe_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"latest_2026.json").write_text(json.dumps(
              {"season":2026,"rows":50,"captured_at":"now",
               "files":["latest_2026_00.csv"]}))
            rows,err=read_published_snapshot(root)
            self.assertEqual(rows,[])
            self.assertEqual(err,"snapshot_chunk_missing")
if __name__=="__main__":
    unittest.main()

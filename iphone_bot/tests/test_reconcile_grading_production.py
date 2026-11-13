import copy
import unittest
from iphone_bot.reconcile_grading_production import reconcile

DAY="2026-11-10"
NOW="2026-11-11T10:00:00Z"
START="2026-11-11T01:00:00Z"
CAP="2026-11-10T22:00:00Z"
QUOTE="2026-11-10T21:59:00Z"
GAME="Boston Celtics @ Philadelphia 76ers"
def dataset():
    forecast={"player_id":"42","player":"Player A","team":"BOS",
              "game":GAME,"start":START,"stat":"PTS","projection":20.0,
              "line":None,"is_pregame_prediction":True,"captured_at":CAP}
    actual={**forecast,"status":"GRADED","actual":24,
            "absolute_error":4,"error":-4,
            "final_source":"NBA_CDN_FINAL","source_game_id":"0022601111"}
    original={"player_id":"42","player":"Player A","team":"BOS","game":GAME,
              "start":START,"stat":"PTS","projection":20.0,"line":21.5,
              "pickem_tier":"standard","standard_line_two_sided_verified":True,
              "captured_at":CAP,"market_updated":QUOTE,"grade":"GRADED",
              "actual":24,"absolute_error":4,"direction_hit":True,
              "final_source":"NBA_CDN_FINAL","source_game_id":"0022601111",
              "estimated_hit_chance":{"modeled_direction":"More"}}
    return ({"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE","predictions":[forecast]},
            {"version":1,"records":[actual]},
            {"status":"FROZEN_NEW_AI_ALL_MARKET","records":[original]},
            {"game_date_eastern":DAY,"recorded_pregame_forecasts":1,"graded":1,"ungraded":0},
            {"counts":{"frozen_picks":1,"graded":1,"verified_dnp_excluded":0,"pending":0}})
def audit(data=None,checked_at=NOW):
    return reconcile(*(data or dataset()),game_date=DAY,checked_at=checked_at)
class ReconciliationTests(unittest.TestCase):
    def test_rolling_feed_restores_only_original_committed_historical_rows(self):
        import tempfile,subprocess,json
        from pathlib import Path
        from datetime import datetime,timezone
        from unittest.mock import patch
        from iphone_bot.reconcile_grading_production import recover_historical_archive
        original=dataset()[0];current={**original,"predictions":[]}
        def git(*args,**kwargs):
            if args[0][1]=="rev-list":return "a"*40+"\n"
            if args[0][1]=="show":return json.dumps(original)
            raise AssertionError(args)
        now=datetime(2026,11,13,5,tzinfo=timezone.utc)
        with patch("subprocess.check_output",side_effect=git):
            recovered=recover_historical_archive(DAY,current,now)
        self.assertEqual(recovered["predictions"],original["predictions"])
        self.assertEqual(recovered["historical_capture_source_commit"],"a"*40)
        self.assertEqual(current["predictions"],[])
        with patch("subprocess.check_output",side_effect=subprocess.CalledProcessError(1,"git")):
            self.assertEqual(recover_historical_archive(DAY,current,now),current)
        self.assertEqual(recover_historical_archive("2026-11-12",current,now),current)

    def test_midnight_report_selection_preserves_original_counts(self):
        from iphone_bot.reconcile_grading_production import select_dated_report
        stale={"game_date_eastern":"2026-11-11","graded":808}
        correct={"game_date_eastern":"2026-11-12","graded":332,"generated_at":"2026-11-13T04:57:58Z"}
        self.assertEqual(select_dated_report("2026-11-12",[stale,correct]),correct)
        self.assertEqual(select_dated_report("2026-11-13",[stale,correct]),{})
        older={**correct,"graded":300,"generated_at":"2026-11-13T04:30:00Z"}
        self.assertEqual(select_dated_report("2026-11-12",[correct,older]),correct)

    def test_historical_report_rebuild_does_not_create_forecasts_or_grades(self):
        from datetime import datetime, timezone
        from iphone_bot.reconcile_grading_production import historical_status
        data=dataset(); before=copy.deepcopy(data)
        summary=historical_status(DAY,data[0],data[1],datetime(2026,11,12,tzinfo=timezone.utc))
        self.assertEqual(summary["recorded_pregame_forecasts"],1)
        self.assertEqual(summary["graded"],1)
        self.assertEqual(summary["new_grades"],0)
        self.assertEqual(data,before)
        missing=historical_status(DAY,data[0],{"records":[]},datetime(2026,11,12,tzinfo=timezone.utc))
        self.assertEqual(missing["ungraded"],1)
        self.assertEqual(missing["graded"],0)

    def test_grader_nonparticipation_reason_field_is_recognized(self):
        from iphone_bot.reconcile_grading_production import observed_final
        row={"status":"EXCLUDED_VERIFIED_NONPARTICIPANT",
             "final_source":"NBA_OFFICIAL_PRETIP_TRADE_CROSSCHECKED",
             "source_game_id":"0022600215","actual":None,
             "verified_nonparticipation_reason":"VERIFIED_PRETIP_TRADE_NOT_AVAILABLE_FOR_ORIGINAL_TEAM"}
        self.assertTrue(observed_final(row))
        self.assertFalse(observed_final({**row,"actual":0}))
        self.assertFalse(observed_final({**row,"verified_nonparticipation_reason":None}))

    def test_explicit_provider_final_dnp_is_valid_but_absence_or_zero_is_not(self):
        from iphone_bot.reconcile_grading_production import observed_final
        for source in ("ESPN_FINAL", "NBA_CDN_FINAL"):
            row={"status":"EXCLUDED_VERIFIED_DNP","final_source":source,
                 "source_game_id":"401909968","verified_dnp_reason":"COACH'S DECISION",
                 "actual":None}
            self.assertTrue(observed_final(row))
            self.assertFalse(observed_final({**row,"actual":0}))
            self.assertFalse(observed_final({**row,"verified_dnp_reason":None}))
            self.assertFalse(observed_final({**row,"source_game_id":None}))
            self.assertFalse(observed_final({**row,"final_source":"UNVERIFIED"}))

    def test_one_date_two_ledgers_are_independent_and_reconciled(self):
        out=audit()
        self.assertEqual(out["status"],"READY")
        self.assertEqual(out["ai_only"]["graded"],1)
        self.assertEqual(out["standard_line"]["graded"],1)
        self.assertFalse(out["blockers"])
    def test_unresolved_forecast_is_explicit_and_not_assumed_dnp(self):
        v=list(dataset());v[1]={"version":1,"records":[]}
        v[3]={"game_date_eastern":DAY,"recorded_pregame_forecasts":1,"graded":0,"ungraded":1}
        out=audit(v)
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["ai_only"]["overdue"],1)
        self.assertEqual(out["unresolved_ai_only"][0]["reason"],"VERIFIED_COMPLETED_GAME_PLAYER_COVERAGE_NOT_ESTABLISHED")
    def test_pending_standard_has_distinct_final_grading_gate(self):
        v=list(dataset());p=v[2]["records"][0]
        p.update(grade="PENDING",actual=None,absolute_error=None,direction_hit=None,final_source=None)
        v[4]={"counts":{"frozen_picks":1,"graded":0,"verified_dnp_excluded":0,"pending":1}}
        out=audit(v)
        self.assertEqual(out["standard_line"]["overdue"],1)
        self.assertIn("STANDARD_VERIFIED_FINAL_NOT_APPLIED",out["blockers"])
    def test_green_job_does_not_hide_stale_report(self):
        v=list(dataset());v[3]["graded"]=0;v[3]["ungraded"]=1
        out=audit(v)
        self.assertIn("AI_STATUS_REPORT_LEDGER_DRIFT",out["blockers"])
    def test_report_dates_cannot_be_mixed(self):
        v=list(dataset());v[3]["game_date_eastern"]="2026-11-11"
        self.assertIn("AI_STATUS_REPORT_MISSING_FOR_DATE",audit(v)["blockers"])
    def test_audit_rejects_graded_wrong_math(self):
        v=list(dataset());v[2]["records"][0]["direction_hit"]=False
        out=audit(v)
        self.assertIn("STANDARD_DIRECTION_GRADE_MISMATCH",out["blockers"])
    def test_independent_verified_final_source_required(self):
        v=list(dataset());v[1]["records"][0]["final_source"]="SCORES_LIVE"
        out=audit(v)
        self.assertEqual(out["ai_only"]["graded"],0)
        self.assertIn("INVALID_VERIFIED_FINAL_RECORD",out["blockers"])
    def test_dnp_requires_independent_evidence_not_zero(self):
        v=list(dataset());row=v[1]["records"][0]
        row.update(status="EXCLUDED_VERIFIED_DNP",final_source="NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
                   actual=None,absolute_error=None,verified_dnp_reason="OFFICIAL_INACTIVE")
        v[3].update(graded=0,ungraded=0)
        out=audit(v)
        self.assertEqual(out["ai_only"]["verified_exclusion"],1)
        self.assertEqual(out["ai_only"]["unresolved"],0)
        self.assertEqual(out["ai_only"]["graded"],0)
    def test_duplicate_final_identity_is_quarantined(self):
        v=list(dataset());v[1]["records"].append(copy.deepcopy(v[1]["records"][0]))
        out=audit(v)
        self.assertIn("DUPLICATE_OR_CONFLICTING_FINAL_IDENTITY",out["blockers"])
        self.assertEqual(out["ai_only"]["unresolved"],1)
    def test_verified_integer_line_push_is_neither_win_nor_loss(self):
        v=list(dataset());p=v[2]["records"][0]
        p["line"]=24
        p["direction_hit"]=None
        out=audit(v)
        self.assertEqual(out["standard_line"]["push"],1)
        self.assertNotIn("STANDARD_DIRECTION_GRADE_MISMATCH",out["blockers"])
        self.assertEqual(out["status"],"READY")
    def test_integer_line_push_mislabeled_win_is_rejected(self):
        v=list(dataset());p=v[2]["records"][0]
        p["line"]=24
        p["direction_hit"]=True
        out=audit(v)
        self.assertIn("STANDARD_DIRECTION_GRADE_MISMATCH",out["blockers"])

    def test_wrong_market_tier_cannot_be_called_graded(self):
        v=list(dataset());v[2]["records"][0]["pickem_tier"]="demon"
        out=audit(v)
        self.assertIn("INVALID_OR_LATE_STANDARD_PICK",out["blockers"])
    def test_naive_pretip_capture_rejected(self):
        v=list(dataset());v[0]["predictions"][0]["captured_at"]="2026-11-10T22:00:00"
        self.assertIn("INVALID_OR_LATE_PREGAME_AI",audit(v)["blockers"])
    def test_complete_verified_game_missing_player_is_not_assumed_a_dnp(self):
        from iphone_bot.reconcile_grading_production import independently_verified_team_games, missing_player_evidence
        boxes=[]
        for t,o in (("BOS","PHI"),("PHI","BOS")):
            for i in range(8):
                boxes.append({"player":t+str(i),"team":t,"opponent":o,
                    "date":"2026-11-10","source_game_id":"0022600212",
                    "source":"NBA_CDN_FINAL","final_confirmed":True,
                    "PTS":10,"REB":2,"AST":1,"PRA":13,"MIN":20})
        evidence=independently_verified_team_games({"version":1,"rows":boxes},DAY)
        reason,gid=missing_player_evidence("Not In Final", "BOS",evidence)
        self.assertEqual(reason,"VERIFIED_FINAL_GAME_PLAYER_ABSENT_FROM_PLAYED_ROWS_DNP_NOT_PROVEN")
        self.assertEqual(gid,"0022600212")
        self.assertEqual(missing_player_evidence("BOS0","BOS",evidence)[0],
                         "VERIFIED_PLAYER_PLAYED_BUT_GRADE_IDENTITY_NOT_MATCHED")
        self.assertEqual(missing_player_evidence("Unknown","TOR",evidence)[0],
                         "VERIFIED_COMPLETED_GAME_PLAYER_COVERAGE_NOT_ESTABLISHED")

    def test_incomplete_final_game_cannot_prove_absence(self):
        from iphone_bot.reconcile_grading_production import independently_verified_team_games
        boxes=[]
        for t,o in (("BOS","PHI"),("PHI","BOS")):
            for i in range(5):
                boxes.append({"player":t+str(i),"team":t,"opponent":o,
                    "date":"2026-11-10","source_game_id":"0022600212",
                    "source":"NBA_CDN_FINAL","final_confirmed":True,
                    "PTS":10,"REB":2,"AST":1,"PRA":13,"MIN":20})
        self.assertEqual(independently_verified_team_games({"version":1,"rows":boxes},DAY),{})

    def test_non_overdue_pending_is_not_proclaimed_complete(self):
        v=list(dataset());v[1]["records"]=[]
        v[3].update(graded=0,ungraded=1)
        result=audit(v,"2026-11-11T02:00:00Z")
        self.assertEqual(result["ai_only"]["overdue"],0)
        self.assertEqual(result["status"],"AWAITING_VERIFIED_FINALS")
        self.assertEqual(result["ai_only"]["unresolved"],1)
        # This is a pending/awaiting state, never an all-graded claim.
if __name__=="__main__":unittest.main()

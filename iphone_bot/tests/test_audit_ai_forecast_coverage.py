import datetime as dt
import json
import unittest
from pathlib import Path
from iphone_bot.audit_ai_forecast_coverage import audit

NOW=dt.datetime(2026,11,10,11,tzinfo=dt.timezone.utc)

def p(stat="PTS"):
    return {"player":"Example Player","player_id":"123","team":"GSW",
            "game":"New Orleans Pelicans @ Golden State Warriors",
            "start":"2026-11-10T03:00:00Z","stat":stat,
            "captured_at":"2026-11-09T22:00:00Z",
            "is_pregame_prediction":True,"line":None,"projection":25.5}
def grade(x,**overrides):
    return {**x,"status":"GRADED","actual":23,"final_source":"NBA_CDN_FINAL",
            "source_game_id":"0022600200",**overrides}
def daily(**changes):
    return {"game_date_eastern":"2026-11-09","recorded_pregame_forecasts":2,
            "graded":1,"verified_dnp_exclusions":0,
            "verified_pretip_transfer_exclusions":0,"ungraded":1,**changes}
class ForecastCoverageAuditTests(unittest.TestCase):
    def test_pending_preserved_not_graduated_or_voided(self):
        rows=[p(),p("AST")]
        out=audit({"predictions":rows},{"records":[grade(rows[0])]},
                  daily(),now=NOW)
        d=out["days"]["2026-11-09"]
        self.assertEqual(d["captured"],2)
        self.assertEqual(d["graded"],1)
        self.assertEqual(d["pending"],1)
        self.assertEqual(d["pending_by_game"],{rows[0]["game"]:1})
        self.assertEqual(out["status"],"VERIFIED_FINAL_ROWS_OUTSTANDING")
    def test_report_claiming_all_graded_cannot_pass(self):
        rows=[p(),p("AST")]
        with self.assertRaisesRegex(ValueError,"AI_DAY_STATUS_LEDGER_DISAGREEMENT"):
            audit({"predictions":rows},{"records":[grade(rows[0])]},
                  daily(graded=2,ungraded=0),now=NOW)
    def test_preserves_verified_dnp_without_counting_as_win(self):
        x=p()
        r=grade(x,status="EXCLUDED_VERIFIED_DNP",actual=None)
        out=audit({"predictions":[x]},{"records":[r]},now=NOW)
        d=out["days"]["2026-11-09"]
        self.assertEqual(d["graded"],0)
        self.assertEqual(d["void_dnp"],1)
        self.assertEqual(d["pending"],0)
    def test_rejects_changed_frozen_projection(self):
        x=p()
        with self.assertRaisesRegex(ValueError,"IMMUTABLE_PRETIP_FORECAST_MISMATCH"):
            audit({"predictions":[x]},{"records":[grade(x,projection=27)]},now=NOW)
    def test_rejects_final_outcome_without_source(self):
        x=p()
        with self.assertRaisesRegex(ValueError,"VERIFIED_OUTCOME_MISSING_FINAL_SOURCE"):
            audit({"predictions":[x]},{"records":[grade(x,source_game_id=None)]},now=NOW)
    def test_rolled_archive_does_not_delete_older_verified_grades(self):
        current=p()
        prior=grade({**p(),"start":"2026-11-08T03:00:00Z",
                     "captured_at":"2026-11-07T22:00:00Z"})
        out=audit({"predictions":[current]},
                  {"records":[prior]},now=NOW)
        self.assertEqual(out["verified_historical_outcomes_not_in_rolling_archive"],1)
        self.assertEqual(out["days"]["2026-11-09"]["pending"],1)
    def test_real_repository_records_reconcile_against_day_statuses(self):
        root=Path(__file__).resolve().parents[2]/"docs"
        def read(name):return json.loads((root/name).read_text())
        previous=read("ai_forecast_grade_status.json")
        today=read("ai_forecast_today_grade_status.json")
        # Reconcile this committed snapshot at its observation time. Running
        # the same commit after another tipoff must not invent new eligibility
        # in a historical test fixture; live audit still uses actual now.
        snapshot_time=dt.datetime.fromisoformat(today["generated_at"].replace("Z","+00:00"))
        self.assertIsNotNone(snapshot_time.tzinfo)
        out=audit(read("ai_no_line_pregame_archive.json"),
                  read("ai_forecast_actual_ledger.json"),
                  previous,
                  today,
                  now=snapshot_time)
        # The pregame archive rolls forward; 2026-11-09 will eventually
        # disappear. Never require one historical date to remain forever.
        self.assertTrue(out["days"], "No eligible saved forecasts to audit")
        self.assertIn(previous["game_date_eastern"],out["days"])
        for day,counts in out["days"].items():
            self.assertEqual(counts["captured"],
                             counts["accounted_for"]+counts["pending"],day)
if __name__=="__main__":unittest.main()

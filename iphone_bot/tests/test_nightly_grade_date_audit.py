import unittest

from iphone_bot.nightly_grade_date_audit import audit

DAY="2026-11-08"
def row(status="SETTLED",stamp="2026-11-09T00:00:00Z",game="A @ B"):
    return {"event_start":stamp,"status":status,"game":game}
class NightlyGradeDateAuditTests(unittest.TestCase):
    def test_zero_pending_with_no_capture_not_pass(self):
        r=audit(DAY,{"records":[row(stamp="2026-11-08T02:00:00Z")]})
        self.assertEqual(r["verdict"],"NO_LOCKED_PAPER_PICKS_CAPTURED")
        self.assertEqual(r["locked_paper_records"],0)

    def test_eastern_time_not_utc_day(self):
        r=audit(DAY,{"records":[row()]})
        self.assertEqual(r["locked_paper_records"],1)
        self.assertEqual(r["verdict"],"ALL_CAPTURED_PAPER_PICKS_RESOLVED")

    def test_pending_is_not_graded(self):
        r=audit(DAY,{"records":[row(),row("PENDING",game="C @ D")]})
        self.assertEqual(r["verdict"],"PENDING_FINAL_PLAYER_RESULTS")
        self.assertEqual(r["pending_games"],["C @ D"])

    def test_void_only_not_counted_as_win(self):
        r=audit(DAY,{"records":[row("VOID_DNP")]})
        self.assertEqual(r["settled_or_verified_void"],1)
        self.assertEqual(r["paper_status_counts"],{"VOID_DNP":1})

    def test_unpriced_forecast_not_invented_as_locked_pick(self):
        r=audit(DAY,{"records":[]},archive={"predictions":[
            {"start":"2026-11-09T00:00:00Z","line":None},
            {"start":"2026-11-09T00:00:00Z","line":23.5}]})
        self.assertEqual(r["unpriced_pregame_archive_forecasts"],1)
        self.assertEqual(r["verdict"],"NO_LOCKED_PAPER_PICKS_CAPTURED")

    def test_prizepicks_cumulative_not_claimed_date_specific(self):
        r=audit(DAY,{"records":[]},prizepicks_summary={"status":"GRADED","pending":0})
        self.assertFalse(r["prizepicks_date_specific_verified"])
        self.assertEqual(r["prizepicks_cumulative_pending"],0)

    def test_november_8_prizepicks_pending_is_not_marked_complete(self):
        pp={"records":[
            {"start":"2026-11-09T00:00:00Z","status":"SETTLED","game":"A @ B"},
            {"start":"2026-11-09T01:00:00Z","status":"PENDING","game":"C @ D"}
        ]}
        r=audit(DAY,{"records":[]},prizepicks_ledger=pp)
        self.assertEqual(r["prizepicks_date_locked_records"],2)
        self.assertEqual(r["prizepicks_date_pending"],1)
        self.assertEqual(r["prizepicks_date_pending_games"],["C @ D"])
        self.assertEqual(r["prizepicks_pending_record_counts_by_game"],{"C @ D":1})
        self.assertFalse(r["prizepicks_date_specific_verified"])

    def test_prizepicks_settled_all_date_verified_separately_from_sportsbook(self):
        pp={"records":[{"start":"2026-11-09T00:00:00Z",
                        "status":"SETTLED","game":"A @ B"}]}
        r=audit(DAY,{"records":[]},prizepicks_ledger=pp)
        self.assertTrue(r["prizepicks_date_specific_verified"])
        self.assertEqual(r["verdict"],"NO_LOCKED_PAPER_PICKS_CAPTURED")

    def test_latest_completed_form_date_lag_reported(self):
        r=audit(DAY,{"records":[row("PENDING")]},form={"latest_game_date":"2026-11-07"})
        self.assertFalse(r["form_confirmed_through_target_day"])

if __name__=="__main__":
    unittest.main()

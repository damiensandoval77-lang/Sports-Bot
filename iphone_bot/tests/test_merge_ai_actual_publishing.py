import unittest
from iphone_bot.merge_ai_actual_publishing import merge

def row(status="PENDING",actual=None):
    r={"status":status,"player_id":"123","player":"Test Player","team":"GSW",
       "game":"New Orleans Pelicans @ Golden State Warriors",
       "start":"2026-11-10T03:00:00Z","stat":"PTS",
       "captured_at":"2026-11-09T22:20:00Z",
       "projection":29.1,"line":None,
       "actual":actual,"error":None,"absolute_error":None,
       "final_source":None,"source_game_id":None,"minutes":None}
    if status=="GRADED":
        r.update(actual=31.0,error=-1.9,absolute_error=1.9,
                 final_source="NBA_CDN_FINAL",source_game_id="0022600200",
                 minutes=33.0)
    return r

class PublishedFinalGradesTests(unittest.TestCase):
    def test_promotes_old_pending_to_verified_final(self):
        output=merge({"records":[row()]},{"records":[row("GRADED")]})
        self.assertEqual(output["records"][0]["status"],"GRADED")
        self.assertEqual(output["records"][0]["actual"],31.0)
    def test_later_stale_pending_cannot_erase_verified_final(self):
        output=merge({"records":[row("GRADED")]},{"records":[row()]})
        self.assertEqual(output["records"][0]["actual"],31.0)
    def test_repeated_same_final_is_idempotent(self):
        output=merge({"records":[row("GRADED")]},{"records":[row("GRADED")]})
        self.assertEqual(len(output["records"]),1)
    def test_conflicting_verified_stats_fail_closed(self):
        newer={**row("GRADED"),"actual":40.0}
        with self.assertRaisesRegex(ValueError,"Conflicting verified final"):
            merge({"records":[row("GRADED")]},{"records":[newer]})
    def test_frozen_projection_changes_never_published(self):
        newer={**row("GRADED"),"projection":30.5}
        with self.assertRaisesRegex(ValueError,"Conflicting frozen forecast"):
            merge({"records":[row()]},{"records":[newer]})
    def test_confirmed_dnp_cannot_be_rewritten_as_played(self):
        excluded={**row(),"status":"EXCLUDED_VERIFIED_DNP",
                  "final_source":"NBA_CDN_FINAL","source_game_id":"0022600200",
                  "verified_dnp_reason":"INACTIVE"}
        with self.assertRaisesRegex(ValueError,"Conflicting verified final"):
            merge({"records":[excluded]},{"records":[row("GRADED")]})
    def test_different_markets_remain_independent(self):
        first=row("GRADED")
        second={**row(),"stat":"REB","projection":6.1}
        out=merge({"records":[first]},{"records":[second]})
        self.assertEqual(len(out["records"]),2)
        self.assertEqual({r["stat"] for r in out["records"]},{"PTS","REB"})
    def test_real_published_final_ledger_is_idempotent(self):
        import json
        from pathlib import Path
        ledger=json.loads((Path(__file__).resolve().parents[2]/
                           "docs/ai_forecast_actual_ledger.json").read_text())
        merged=merge(ledger,ledger)
        self.assertEqual(len(merged["records"]),len(ledger["records"]))
        self.assertEqual(
            sum(r["status"]=="GRADED" for r in merged["records"]),
            sum(r["status"]=="GRADED" for r in ledger["records"]))
    def test_unknown_outcome_does_not_get_guessed(self):
        with self.assertRaisesRegex(ValueError,"Unknown"):
            merge({"records":[]},{"records":[{**row(),"status":"WIN"}]})

if __name__=="__main__":
    unittest.main()

import unittest
from datetime import datetime,timezone
try:
    from iphone_bot.free_official_nba_injury_watch import update
except ImportError:
    from free_official_nba_injury_watch import update
NOW=datetime(2026,11,9,23,0,tzinfo=timezone.utc)
def report(status,issued="2026-11-09T22:00:00Z"):
    return {"status":"OFFICIAL_NBA_REPORT_VERIFIED","injury_data_verified":True,
      "report_issued_at":issued,
      "players":[{"player":"Austin Reaves","player_id":"1630559","team":"LAL",
                  "game_date":"2026-11-09","status":status}]}
class FreeOfficialWatchTests(unittest.TestCase):
    def test_daytime_freshness_and_research_recovery_wiring(self):
        from pathlib import Path
        text=Path('.github/workflows/nba-free-official-injury-watch.yml').read_text()
        self.assertIn("17 6-15 * * *",text)
        self.assertIn("INJURY_CONTEXT_UNVERIFIED_OR_STALE",text)
        self.assertIn("short_history_model.json",text)
        self.assertIn("provisional_short_history.json",text)
        self.assertIn("Model refresh already active; no duplicate dispatch",text)
    def test_first_snapshot_does_not_invent_a_change(self):
        r,changed,_=update({},report("Out"),NOW)
        self.assertTrue(changed)
        self.assertEqual(r["new_changes"],[])
        self.assertEqual(r["events"],[])
    def test_questionable_to_out_creates_source_anchored_event(self):
        prev,_,_=update({},report("Questionable"),NOW)
        current=report("Out","2026-11-09T22:30:00Z")
        r,changed,_=update(prev,current,NOW)
        self.assertTrue(changed)
        self.assertEqual(len(r["events"]),1)
        self.assertEqual(r["events"][0]["player_id"],"1630559")
        self.assertEqual(r["events"][0]["previous_status"],"QUESTIONABLE")
        self.assertTrue(r["events"][0]["official"])
    def test_newer_available_clears_out_event(self):
        prev,_,_=update({},report("Questionable"),NOW)
        out,_,_=update(prev,report("Out","2026-11-09T22:15:00Z"),NOW)
        restored,_,_=update(out,report("Available","2026-11-09T22:30:00Z"),NOW)
        self.assertEqual(restored["events"],[])
        self.assertEqual(restored["new_changes"][0]["status"],"AVAILABLE")
    def test_no_older_report_can_override(self):
        prev,_,_=update({},report("Out","2026-11-09T22:30:00Z"),NOW)
        r,changed,_=update(prev,report("Available","2026-11-09T22:15:00Z"),NOW)
        self.assertFalse(changed)
        self.assertEqual(r,prev)
    def test_espn_unverified_cannot_override(self):
        prev,_,_=update({},report("Out"),NOW)
        r,changed,_=update(prev,{"status":"THIRD_PARTY_ESPN_INJURY_CONTEXT",
          "injury_data_verified":False,"players":[]},NOW)
        self.assertFalse(changed)
        self.assertEqual(r,prev)
if __name__=="__main__":unittest.main()

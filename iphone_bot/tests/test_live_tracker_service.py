import unittest
from datetime import datetime,timezone
from iphone_bot.live_tracker_service import collect

NOW=datetime(2026,11,9,1,10,tzinfo=timezone.utc)
MATCHUP="Brooklyn Nets @ Dallas Mavericks"
EVENT_ID="401999123"
def event():
    return {"id":EVENT_ID,"status":{"type":{"state":"in","shortDetail":"Q2 9:10"},
             "period":2,"displayClock":"9:10","clock":550},
            "competitions":[{"competitors":[
                {"homeAway":"away","team":{"displayName":"Brooklyn Nets"}},
                {"homeAway":"home","team":{"displayName":"Dallas Mavericks"}}]}]}
def summary():
    return {"header":{"competitions":[{"competitors":[
        {"homeAway":"away","team":{"displayName":"Brooklyn Nets"}},
        {"homeAway":"home","team":{"displayName":"Dallas Mavericks"}}]}]},
        "boxscore":{"players":[{"team":{"abbreviation":"DAL"},
            "statistics":[{"labels":["PTS","REB","AST"],
                "athletes":[{"athlete":{"id":"5041939","displayName":"Cooper Flagg"},
                              "stats":["9","3","1"]}]}]}]}}

class AlwaysOnLiveDataTests(unittest.TestCase):
    def test_exact_dallas_player_observation_and_coverage(self):
        def request(path):
            return {"events":[event()]} if "scoreboard" in path else summary()
        report=collect(None,request,NOW)
        self.assertEqual(report["coverage_status"],"COMPLETE")
        self.assertEqual(report["games"][0]["game"],MATCHUP)
        self.assertEqual(report["games"][0]["player_rows"][0]["PRA"],13)
        self.assertEqual(report["games"][0]["observed_at"],NOW.isoformat())
        self.assertFalse(report["games"][0]["stale"])
    def test_errored_boxscore_is_explicit_missing(self):
        def request(path):
            if "summary" in path:raise OSError("blocked")
            return {"events":[event()]}
        report=collect(None,request,NOW)
        self.assertEqual(report["coverage_status"],"PARTIAL_LIVE_DATA")
        self.assertEqual(report["coverage"]["missing_fresh_matchups"],[MATCHUP])
        self.assertEqual(report["games"],[])
        self.assertIn("OSError",[e["reason"] for e in report["errors"]])
    def test_older_actuals_retained_with_original_timestamp(self):
        older=NOW.replace(minute=0)
        previous=collect(None,lambda p:{"events":[event()]} if "scoreboard" in p else summary(),older)
        def request(path):
            if "summary" in path:raise OSError("offline")
            return {"events":[event()]}
        report=collect(previous,request,NOW)
        self.assertEqual(report["games"][0]["observed_at"],older.isoformat())
        self.assertTrue(report["games"][0]["stale"])
        self.assertFalse(report["coverage"]["complete"])
if __name__=="__main__":unittest.main()

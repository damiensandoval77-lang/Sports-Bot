import gzip
import json
import tempfile
import unittest
from pathlib import Path
from iphone_bot.archived_espn_game_ids import archived_espn_hints,combine_espn_hints

DATE="2026-11-09"
KEY=(DATE,"CLE","CHA")
def snapshot(event_id="401909953",status="THIRD_PARTY_NBA_SCHEDULE_ONLY"):
    return {"status":"ORIGINAL_REPORTED_NBA_FIXTURES_ARCHIVE",
        "schedule":{"status":status,"games":[
            {"id":event_id,"date_eastern":DATE,
             "start":"2026-11-10T00:00:00Z",
             "away_abbreviation":"CLE","home_abbreviation":"CHA",
             "game":"Cleveland Cavaliers @ Charlotte Hornets"}]}}

def put(root,filename,obj):
    p=Path(root)/DATE/filename
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(gzip.compress(json.dumps(obj).encode()))
    return p

class ArchivedEspnIDsTests(unittest.TestCase):
    def test_exact_historical_schedule_id_survives_rollover(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"01.json.gz",snapshot())
            self.assertEqual(archived_espn_hints(root,{DATE}),{KEY:"401909953"})
            self.assertEqual(archived_espn_hints(root,{"2026-11-08"}),{})
    def test_conflicting_archives_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"01.json.gz",snapshot())
            put(root,"02.json.gz",snapshot("401909999"))
            self.assertEqual(archived_espn_hints(root,{DATE}),{})
    def test_incorrect_archive_status_and_non_espn_ids_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            put(root,"01.json.gz",snapshot(status="SCHEDULE_UNAVAILABLE"))
            put(root,"02.json.gz",snapshot(event_id="0022600204"))
            put(root,"03.json.gz",{"status":"UNKNOWN","schedule":snapshot()["schedule"]})
            self.assertEqual(archived_espn_hints(root,{DATE}),{})
    def test_current_vs_archive_conflict_rejected(self):
        self.assertEqual(combine_espn_hints({KEY:"401909999"},{KEY:"401909953"}),{})
        self.assertEqual(combine_espn_hints({KEY:"401909953"},{KEY:"401909953"}),
                         {KEY:"401909953"})
if __name__=="__main__":unittest.main()

import copy
import datetime as dt
import json
import unittest
from pathlib import Path
from iphone_bot.audit_failure_domains import verified_posttip_slate

class FailureDomainPhaseTests(unittest.TestCase):
    def test_only_complete_fresh_verified_posttip_slate_relaxes_offer_freshness(self):
        root=Path(__file__).resolve().parents[2]/"docs"
        season=json.loads((root/"nba_season_schedule_2026_27.json").read_text())
        now=dt.datetime(2026,11,13,4,45,tzinfo=dt.timezone.utc)
        games=[g for g in season["games"] if g["date_eastern"]=="2026-11-12"]
        schedule={"coverage_complete":True,"generated_at":now.isoformat(),"games":games}
        self.assertTrue(verified_posttip_slate(schedule,season,now))
        self.assertFalse(verified_posttip_slate({**schedule,"games":games[:-1]},season,now))
        self.assertFalse(verified_posttip_slate({**schedule,"generated_at":"2026-11-12T00:00:00Z"},season,now))
        self.assertFalse(verified_posttip_slate(schedule,{},now))
        pre=now-dt.timedelta(hours=12)
        self.assertFalse(verified_posttip_slate({**schedule,"generated_at":pre.isoformat()},season,pre))
        mismatch=copy.deepcopy(schedule);mismatch["games"][0]["home_abbreviation"]="INVALID"
        self.assertFalse(verified_posttip_slate(mismatch,season,now))

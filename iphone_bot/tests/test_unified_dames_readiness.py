import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from iphone_bot.unified_dames_readiness import evaluate,CORE_NBA,CORE_NFL

class UnifiedIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        def put(path,data):
            file=self.root/path;file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(data,encoding="utf-8")
        self.put=put
        put("dames-picks/index.html",'feeds.js dames_take.js getJSON("nfl/data/latest_2026.json") getJSON("lagged_matchup_all_market_ledger.json")')
        put("dames-picks/feeds.js","adapter")
        put("dames-picks/dames_take.js","model")
        for path in ("index.html","nfl/index.html"):
            put(path,'location.replace("./dames-picks/")')
        for key,path in CORE_NBA.items():
            obj={"records":[]} if key=="frozen_models" else {"games":[]} if key=="schedule" else {"status":"CAPTURE_VERIFIED"} if key=="capture_audit" else {}
            put(path,json.dumps(obj))
        for key,path in CORE_NFL.items():
            if path.endswith(".csv"):put(path,"player,line\n")
            else:put(path,json.dumps({"files":["chunk.csv"]} if key=="prop_manifest" else {"games":[{"id":"g"}]} if key=="schedule" else {}))
        put("nfl/data/chunk.csv","player,line\n")
    def test_both_sports_and_redirects_healthy(self):
        self.assertEqual(evaluate(self.root)["status"],"READY")
    def test_nfl_missing_shard_cannot_hide_behind_nba(self):
        (self.root/"nfl/data/chunk.csv").unlink()
        r=evaluate(self.root)
        self.assertEqual(r["sports"]["NBA"]["state"],"READY")
        self.assertEqual(r["sports"]["NFL"]["state"],"DEGRADED")
        self.assertEqual(r["status"],"DEGRADED")
    def test_nba_capture_gap_is_visible(self):
        self.put("tonight_capture_gradeability.json",json.dumps({"status":"CAPTURE_INCOMPLETE"}))
        r=evaluate(self.root)
        self.assertIn("PRETIP_CAPTURE_NOT_VERIFIED",r["sports"]["NBA"]["issues"])
    def test_old_dashboard_link_is_regression(self):
        self.put("dames-picks/index.html",'feeds.js dames_take.js getJSON("nfl/data/latest_2026.json") getJSON("lagged_matchup_all_market_ledger.json") ../nfl/index.html')
        self.assertIn("RETIRED_DASHBOARD_LINK_REINTRODUCED",evaluate(self.root)["app"]["issues"])
if __name__=="__main__":unittest.main()

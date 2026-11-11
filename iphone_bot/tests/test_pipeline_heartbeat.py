"""Tests for deployed-site pipeline heartbeat, failed-run discovery and data gaps."""
import datetime as dt
import unittest
from iphone_bot.pipeline_heartbeat import evaluate
NOW=dt.datetime(2026,11,11,23,30,tzinfo=dt.timezone.utc)
def time(**kw):return (NOW+dt.timedelta(**kw)).isoformat()
GAME="Miami Heat @ Utah Jazz"
def site(start=None,snapshot=None,ledger=None,model=None):
    start=start or time(minutes=30)
    return {"prizepicks.json":{"generated_at":time(minutes=-15),"board_offers":[{"game":GAME}]},
            "prizepicks_site.json":{"generated_at":snapshot or time(minutes=-10),"board_offers":[{"game":GAME}]},
            "lagged_matchup_all_market_ledger.json":{"records":ledger or []},
            "lagged_matchup_live_all_markets.json":model or {},
            "nba_schedule.json":{"games":[{"game":GAME,"start":start}]},
            "nba_scoreboard_independent.json":{},"nba_player_tracking_independent.json":{}}
def stage(r,name):return next(x for x in r["stages"] if x["stage"]==name)
class Heartbeat(unittest.TestCase):
    def test_old_published_lines_fail(self):
        self.assertEqual(stage(evaluate(NOW,site(snapshot=time(hours=-6))),"lines_publish")["status"],"FAIL")
    def test_missing_picks_three_hours_before_tip_fail(self):
        self.assertEqual(stage(evaluate(NOW,site()),"picks_frozen")["status"],"FAIL")
    def test_missing_picks_five_hours_before_tip_warn(self):
        self.assertEqual(stage(evaluate(NOW,site(start=time(hours=5))),"picks_frozen")["status"],"WARN")
    def test_matching_saved_picks_good(self):
        start=time(minutes=30)
        self.assertEqual(stage(evaluate(NOW,site(start=start,ledger=[{"game":GAME,"start":start}])),"picks_frozen")["status"],"OK")
    def test_older_matchup_does_not_count(self):
        self.assertEqual(stage(evaluate(NOW,site(ledger=[{"game":GAME,"start":time(days=-20)}])),"picks_frozen")["status"],"FAIL")
    def test_model_timestamp_cannot_hide_missing_games(self):
        report=evaluate(NOW,site(model={"generated_at":time(minutes=-2)}))
        self.assertEqual(stage(report,"picks_frozen")["status"],"FAIL")
        self.assertTrue(stage(report,"picks_frozen")["evidence"]["missing"])
    def test_overdue_pending_requires_settlement(self):
        r={"game":GAME,"start":time(hours=-10),"grade":"PENDING"}
        self.assertEqual(stage(evaluate(NOW,site(ledger=[r])),"settlement")["status"],"FAIL")
    def test_missing_feeds_report_non_ok(self):
        self.assertEqual(evaluate(NOW,{})["overall"],"FAIL")
if __name__=="__main__":unittest.main()

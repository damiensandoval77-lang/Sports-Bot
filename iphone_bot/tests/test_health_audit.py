import datetime as dt
import unittest

from iphone_bot.health_audit import assess

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 9, 12, 0, tzinfo=UTC)

def feeds(available=0, checked=0):
    odds = {"updated_at": NOW.isoformat(), "slate_events_available": available,
            "slate_events_checked": checked, "market_coverage_limited": False, "picks": []}
    tracking = {"captured_at": NOW.isoformat(), "games": [],
                "coverage": {"active_matchups": [], "missing_fresh_matchups": []}}
    return odds, tracking

class HealthAuditTests(unittest.TestCase):
    def test_no_active_games_is_normal(self):
        odds, tracking = feeds()
        result = assess(odds, tracking, now=NOW)
        self.assertTrue(result["ok"])

    def test_available_games_but_none_checked_is_error(self):
        odds, tracking = feeds(12, 0)
        result = assess(odds, tracking, now=NOW)
        self.assertFalse(result["ok"])
        self.assertIn("ZERO_SLATE_COVERAGE", [f["code"] for f in result["findings"]])

    def test_stale_odds_fails(self):
        odds, tracking = feeds()
        odds["updated_at"] = (NOW-dt.timedelta(hours=5)).isoformat()
        self.assertFalse(assess(odds, tracking, now=NOW)["ok"])

    def test_missing_live_matchup_fails(self):
        odds, tracking = feeds()
        tracking["coverage"]["missing_fresh_matchups"] = ["match-1"]
        self.assertFalse(assess(odds, tracking, now=NOW)["ok"])

    def test_future_observations_cannot_claim_freshness(self):
        for field, code in (("updated_at", "ODDS_TIMESTAMP_FUTURE"),
                            ("captured_at", "TRACKER_TIMESTAMP_FUTURE")):
            with self.subTest(field=field):
                odds, tracking = feeds()
                target = odds if field == "updated_at" else tracking
                target[field] = (NOW + dt.timedelta(minutes=6)).isoformat()
                result = assess(odds, tracking, now=NOW)
                self.assertFalse(result["ok"])
                self.assertIn(code, [f["code"] for f in result["findings"]])

    def test_bounded_clock_skew_is_allowed(self):
        odds, tracking = feeds()
        odds["updated_at"] = (NOW + dt.timedelta(minutes=5)).isoformat()
        tracking["captured_at"] = (NOW + dt.timedelta(minutes=5)).isoformat()
        self.assertTrue(assess(odds, tracking, now=NOW)["ok"])

    def test_partial_coverage_warns(self):
        odds, tracking = feeds(12, 11)
        result = assess(odds, tracking, now=NOW)
        self.assertTrue(result["ok"])
        self.assertIn("PARTIAL_SLATE_COVERAGE", [f["code"] for f in result["findings"]])

if __name__ == "__main__":
    unittest.main()

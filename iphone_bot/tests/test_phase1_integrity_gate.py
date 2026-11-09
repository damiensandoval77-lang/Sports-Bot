import unittest
from datetime import datetime, timezone
from iphone_bot.phase1_integrity_gate import audit

NOW = datetime(2026, 11, 9, 3, 0, tzinfo=timezone.utc)

def valid():
    r = {"event_start": "2026-11-09T04:00:00Z",
         "captured_at": "2026-11-09T02:00:00Z",
         "player_id": "42", "team": "BOS", "market": "PTS",
         "bookmaker": "FanDuel", "line": 20.5,
         "side": "OVER", "original_projection": 23.0,
         "combined_projection": 22.0, "status": "PENDING"}
    return {"generated_at": "2026-11-09T02:59:00Z",
            "records": [r], "captured": 1, "pending": 1,
            "settled": 0, "void_dnp": 0}


class IntegrityGateTests(unittest.TestCase):
    def test_consistent_snapshot(self):
        self.assertEqual(audit(valid(), NOW)["status"], "PASS")

    def test_late_quote_is_rejected(self):
        v = valid()
        v["records"][0]["captured_at"] = "2026-11-09T05:00:00Z"
        self.assertEqual(audit(v, NOW)["status"], "FAIL")

    def test_settled_without_verified_grade_is_rejected(self):
        v = valid()
        v["records"][0]["status"] = "SETTLED"
        v["pending"], v["settled"] = 0, 1
        self.assertEqual(audit(v, NOW)["status"], "FAIL")

    def test_duplicate_identity_is_rejected(self):
        v = valid()
        v["records"].append(dict(v["records"][0]))
        v["captured"], v["pending"] = 2, 2
        self.assertEqual(audit(v, NOW)["status"], "FAIL")

    def test_stale_summary_warns(self):
        v = valid()
        v["generated_at"] = "2026-11-08T22:00:00Z"
        self.assertEqual(audit(v, NOW)["status"], "WARN")

    def test_full_ledger_without_summary_counters(self):
        v = valid()
        for field in ("captured", "pending", "settled", "void_dnp"):
            del v[field]
        self.assertEqual(audit(v, NOW)["status"], "PASS")

    def test_published_sample_is_not_mistaken_for_complete_ledger(self):
        v = valid()
        v["results"] = v.pop("records")
        v["captured"] = 2980
        v["pending"] = 0
        v["settled"] = 2892
        v["void_dnp"] = 88
        self.assertEqual(audit(v, NOW)["status"], "WARN")

    def test_live_system_is_not_claimed_verified(self):
        report = audit(valid(), NOW)
        self.assertFalse(report["live_prizepicks_verified"])
        self.assertFalse(report["replit_deployment_verified"])


if __name__ == "__main__":
    unittest.main()

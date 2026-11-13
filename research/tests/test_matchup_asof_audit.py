import unittest
from research.matchup_asof_audit import audit
from research.matchup_hit_estimate import REQUIRED


def row(captured="2026-11-10T20:00:00Z", start="2026-11-10T23:00:00Z"):
    return {"stat": "AST", "captured_at": captured, "start": start,
            "line": 6.5, "projection": 8.1}


def ledger(*records):
    return {"status": "FROZEN_NEW_AI_ALL_MARKET", "records": list(records)}


def form(updated="2026-11-11T02:40:00Z"):
    return {"updated_at": updated}


def features():
    return {name: {"source": "verified pretip record", "observed_at": "2026-11-10T19:00:00Z",
                   "baseline": 10.0, "matchup": 11.0} for name in REQUIRED}


class AsofAuditTests(unittest.TestCase):
    def test_absent_frozen_features_are_blocked_even_if_postgame_form_exists(self):
        result = audit(ledger(row()), form())
        self.assertEqual(result["frozen_matchup_records_eligible"], 0)
        self.assertEqual(result["blocker_counts"]["no_frozen_matchup_factor_snapshot"], 1)
        self.assertEqual(result["blocker_counts"]["current_form_not_proven_available_at_capture"], 1)

    def test_future_form_timestamp_does_not_disqualify_independent_frozen_features(self):
        r = row()
        r["matchup_factors"] = features()
        result = audit(ledger(r), form())
        self.assertEqual(result["frozen_matchup_records_eligible"], 1)
        self.assertEqual(result["blocker_counts"]["current_form_not_proven_available_at_capture"], 1)
        self.assertFalse(result["production_promotion_approved"])

    def test_postcapture_feature_is_rejected(self):
        r = row()
        r["matchup_factors"] = features()
        r["matchup_factors"]["projected_minutes"]["observed_at"] = "2026-11-10T21:00:00Z"
        result = audit(ledger(r), form())
        self.assertEqual(result["frozen_matchup_records_eligible"], 0)
        self.assertEqual(result["blocker_counts"]["not_asof_projected_minutes"], 1)

    def test_missing_required_feature_is_rejected(self):
        r = row()
        r["matchup_factors"] = features()
        del r["matchup_factors"]["pace_possessions"]
        result = audit(ledger(r), form())
        self.assertEqual(result["blocker_counts"]["missing_pace_possessions"], 1)

    def test_missing_source_is_rejected(self):
        r = row()
        r["matchup_factors"] = features()
        r["matchup_factors"]["depth_role"]["source"] = ""
        self.assertEqual(audit(ledger(r), form())["frozen_matchup_records_eligible"], 0)

    def test_invalid_pretip_freeze_rejected(self):
        r = row(captured="2026-11-11T00:00:00Z")
        r["matchup_factors"] = features()
        self.assertEqual(audit(ledger(r), form())["blocker_counts"]["invalid_pretip_freeze"], 1)

    def test_invalid_numbers_rejected(self):
        r = row()
        r["matchup_factors"] = features()
        r["matchup_factors"]["usage_opportunities"]["baseline"] = 0
        self.assertEqual(audit(ledger(r), form())["frozen_matchup_records_eligible"], 0)

    def test_unexpected_ledger_schema_rejected(self):
        with self.assertRaises(ValueError):
            audit({"records": []}, form())


if __name__ == "__main__":
    unittest.main()

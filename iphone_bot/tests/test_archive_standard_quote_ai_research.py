import datetime as dt
import unittest
from iphone_bot.archive_standard_quote_ai_research import STATUS, merge

NOW = dt.datetime(2026, 11, 10, 18, tzinfo=dt.timezone.utc)
def sample(**changes):
    row = {
        "source": "independent_prizepicksapi_com",
        "provider_projection_id": "pp-1",
        "player": "Example Player", "player_id": "123", "team": "BOS",
        "opponent": "PHI", "game": "Boston Celtics @ Philadelphia 76ers",
        "start": "2026-11-11T01:00:00+00:00", "stat": "PTS",
        "line": 24.5, "projection": 26.2, "ai_direction": "MORE",
        "observed_at": "2026-11-10T17:10:00+00:00",
        "model_generated_at": "2026-11-10T16:00:00+00:00",
        "more_tier": "standard", "less_tier": "standard",
        "research_only": True, "confidence_percent": None, "estimated_ev": None,
        "reliability_screen": {"validated": False, "side": None}
    }
    row.update(changes)
    return row

def incoming(*rows):
    return {"status":"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS", "comparisons":list(rows)}

class ResearchReceiptTests(unittest.TestCase):
    def test_saves_exact_pretip_standard_receipt(self):
        output = merge(incoming(sample()), now=NOW)
        self.assertEqual(output["status"],STATUS)
        self.assertEqual(output["count"],1)
        self.assertEqual(output["records"][0]["line"],24.5)
        self.assertIsNone(output["records"][0]["actual"])
        self.assertIsNone(output["records"][0]["direction_hit"])
        self.assertFalse(output["records"][0]["calibrated"])

    def test_replay_and_outage_do_not_delete_history(self):
        initial=merge(incoming(sample()),now=NOW)
        replay=merge(incoming(sample()),initial,now=NOW)
        self.assertEqual(replay,initial)  # Unchanged archive must be byte-stable
        lost=merge({"status":"STALE_OR_UNVERIFIED_SOURCE","comparisons":[]},replay,now=NOW)
        self.assertEqual(lost["count"],1)
        self.assertEqual(lost["records"][0]["frozen_at"],initial["records"][0]["frozen_at"])

    def test_new_standard_price_is_separate_version(self):
        old=merge(incoming(sample()),now=NOW)
        new=sample(provider_projection_id="pp-2",line=25.5,observed_at="2026-11-10T17:15:00+00:00")
        output=merge(incoming(new),old,now=NOW)
        self.assertEqual({x["line"] for x in output["records"]},{24.5,25.5})

    def test_reject_alternatives_unverified_or_post_tip(self):
        variants=[
            sample(more_tier="goblin",less_tier="goblin"),
            sample(more_tier="demon",less_tier="demon"),
            sample(more_tier="standard",less_tier=None),
            sample(research_only=False),
            sample(reliability_screen={"validated":True}),
            sample(observed_at="2026-11-11T01:01:00+00:00"),
            sample(model_generated_at="2026-11-11T01:01:00+00:00"),
            sample(line=float("nan")),
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertEqual(merge(incoming(variant),now=NOW)["count"],0)
        self.assertEqual(
            merge(incoming(sample()),now=dt.datetime(2026,11,11,1,1,tzinfo=dt.timezone.utc))["count"],0
        )

    def test_repeated_price_retains_original_projection_without_double_count(self):
        original=merge(incoming(sample()),now=NOW)
        changed=sample(provider_projection_id="pp-new",projection=99.0,
                       observed_at="2026-11-10T17:30:00+00:00")
        updated=merge(incoming(changed),original,now=NOW)
        self.assertEqual(updated["count"],1)
        self.assertEqual(updated,original)  # No new commit on an unchanged price
        self.assertEqual(updated["records"][0]["projection"],26.2)
        self.assertEqual(updated["records"][0]["provider_projection_id"],"pp-1")

    def test_future_dated_observations_never_enter_archive(self):
        future = sample(observed_at="2026-11-10T18:01:00+00:00")
        self.assertEqual(merge(incoming(future),now=NOW)["count"],0)
        future_model = sample(model_generated_at="2026-11-10T18:01:00+00:00")
        self.assertEqual(merge(incoming(future_model),now=NOW)["count"],0)

    def test_stale_comparison_snapshot_does_not_create_new_receipt(self):
        source=incoming(sample())
        source["generated_at"]="2026-11-10T15:00:00+00:00"
        self.assertEqual(merge(source,now=NOW)["count"],0)

    def test_bad_existing_archive_never_overwritten(self):
        with self.assertRaises(ValueError):
            merge(incoming(sample()),{"status":"unknown","records":[]},now=NOW)

if __name__ == "__main__":
    unittest.main()

"""Offline regression tests for authenticated PrizePicks fixture attribution."""
import unittest
from datetime import datetime, timedelta, timezone
from iphone_bot.fetch_prizepicks import publish

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
START = (NOW + timedelta(hours=10)).isoformat()

def offer(ident, team="BOS", opponent="MIL", starts=START):
    return {
        "id": ident, "status": "active", "league": "NBA", "is_demo": False,
        "player": {"name": "Example Player", "team": team},
        "event": {"starts_at": starts, "opponent": opponent},
        "market": {"stat": "Points", "period": "Full Game"},
        "observed_at": NOW.isoformat(), "line": 20.5,
        "selections": [{"side": "more", "tier": "standard", "available": True}]
    }

def run(rows):
    return publish([{"meta": {"mode": "live", "source_status": "fresh",
                              "next_cursor": None}, "data": rows}],
                   [], now=NOW,
                   schedule={"games": [{"game": "Boston Celtics @ Milwaukee Bucks",
                                        "start": START}]})

class AttributionDiagnosticsTests(unittest.TestCase):
    def test_attribution_and_unmatched_reasons(self):
        rows = [offer("match"), offer("team", team="NYK"),
                offer("opponent", opponent="NYK"),
                offer("time", starts=(NOW+timedelta(hours=14)).isoformat()),
                offer("missing", opponent="", starts=None)]
        result=run(rows)
        self.assertEqual(result["independent_board_count"], 1)
        self.assertEqual(result["unassigned_or_ambiguous_events"], 4)
        self.assertEqual(result["unassigned_reason_counts"], {
            "missing_opponent_and_tipoff": 1,
            "opponent_mismatch": 1,
            "team_not_in_future_schedule": 1,
            "tipoff_time_mismatch": 1})

    def test_no_fake_assignment_when_no_schedule(self):
        result=publish([{"meta":{"mode":"live","source_status":"fresh"},
                         "data":[offer("match")]}],[],now=NOW,schedule={"games":[]})
        self.assertEqual(result["independent_board_count"],0)
        self.assertEqual(result["unassigned_reason_counts"]["team_not_in_future_schedule"],1)

if __name__=="__main__":
    unittest.main()

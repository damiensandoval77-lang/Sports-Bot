"""Paired shadow metrics must not invent samples or accept leakage."""
import unittest
from datetime import date, timedelta
try:
    from iphone_bot.external_stats_shadow_comparison import compare, ComparisonError
except ImportError:
    from external_stats_shadow_comparison import compare, ComparisonError


def records(n=100):
    origin=date(2026,10,1)
    out=[]
    for i in range(n):
        day=(origin+timedelta(days=i//5)).isoformat()
        out.append({"game_id":f"game{i//5}", "player_id":f"player{i%5}",
            "market":"PTS", "event_start":day+"T19:00:00-04:00",
            "baseline_captured_at":day+"T10:00:00-04:00",
            "challenger_captured_at":day+"T12:00:00-04:00",
            "baseline_projection":"21", "challenger_projection":"20",
            "actual":"20", "line":"20.5", "baseline_over_probability":"0.60",
            "challenger_over_probability":"0.25"})
    return out


class ShadowComparisonTests(unittest.TestCase):
    def test_valid_paired_comparison(self):
        result=compare(records())
        self.assertEqual(result["paired_rows"],100)
        self.assertEqual(result["unique_event_dates"],20)
        self.assertEqual(result["markets"]["PTS"]["baseline"]["mae"],1.0)
        self.assertEqual(result["markets"]["PTS"]["challenger"]["mae"],0.0)
        self.assertEqual(result["markets"]["PTS"]["brier_comparison"]["n"],100)
        self.assertFalse(result["automatic_promotion"])
        self.assertFalse(result["calibrated"])

    def test_late_prediction_rejected(self):
        rows=records()
        rows[0]["challenger_captured_at"]=rows[0]["event_start"]
        with self.assertRaises(ComparisonError): compare(rows)

    def test_naive_time_rejected(self):
        rows=records()
        rows[0]["baseline_captured_at"]="2026-10-01T10:00:00"
        with self.assertRaises(ComparisonError): compare(rows)

    def test_insufficient_pairs_rejected(self):
        with self.assertRaises(ComparisonError):compare(records(90))

    def test_insufficient_dates_rejected(self):
        rows=records()
        for i,r in enumerate(rows):
            day=(date(2026,10,1)+timedelta(days=i//20)).isoformat()
            r["game_id"]=f"game{i//20}"
            r["player_id"]=f"player{i%20}"
            for field,clock in (("event_start","T19:00:00"),("baseline_captured_at","T10:00:00"),("challenger_captured_at","T12:00:00")):
                r[field]=day+clock+"-04:00"
        with self.assertRaises(ComparisonError): compare(rows)

    def test_duplicate_rejected(self):
        rows=records()
        rows[1]=rows[0].copy()
        with self.assertRaises(ComparisonError): compare(rows)

    def test_missing_quote_not_fabricated(self):
        rows=records()
        for r in rows:
            r.pop("line")
        result=compare(rows)
        self.assertIsNone(result["markets"]["PTS"]["brier_comparison"])

    def test_nonfinite_rejected(self):
        rows=records()
        rows[0]["actual"]="nan"
        with self.assertRaises(ComparisonError):compare(rows)


if __name__=="__main__":
    unittest.main()

import unittest
from iphone_bot.confidence_readiness_audit import audit, valid_pregame_proxy
from iphone_bot.combined_probability_audit import METHOD

def pick(**updates):
    row = {"status":"SETTLED","captured_at":"2026-11-06T21:00:00Z",
           "event_start":"2026-11-07T00:10:00Z","player_id":"123",
           "market":"PTS","bookmaker":"FanDuel","line":20.5,
           "actual":25,"combined_projection":24,"side":"OVER",
           "combined_probability_proxy_side":"OVER",
           "combined_probability_proxy_estimate":.95,
           "combined_probability_proxy_method":METHOD}
    row.update(updates)
    return row

class ConfidenceReadinessTests(unittest.TestCase):
    def test_missing_historical_probability_cannot_be_backfilled(self):
        r=audit([pick(combined_probability_proxy_estimate=None)])
        self.assertEqual(r["coverage"]["settled_missing_frozen_probability"],1)
        self.assertEqual(r["overall"]["sample_size"],0)
        self.assertFalse(r["ready_to_fit_calibration"])
        self.assertFalse(r["publish_as_verified_confidence"])

    def test_multiple_books_are_one_observation(self):
        r=audit([pick(),pick(bookmaker="DraftKings",line=21.5)])
        self.assertEqual(r["overall"]["sample_size"],1)
        self.assertEqual(r["high_confidence_90_plus"]["wins"],1)
        self.assertFalse(r["by_confidence_band"]["90-100%"]["verified_confidence"])

    def test_late_capture_wrong_side_nan_are_not_valid(self):
        rows=[pick(captured_at="2026-11-07T01:00:00Z"),
              pick(player_id="2",combined_probability_proxy_side="UNDER"),
              pick(player_id="3",combined_probability_proxy_estimate=float("nan"))]
        self.assertTrue(all(not valid_pregame_proxy(r) for r in rows))
        self.assertEqual(audit(rows)["overall"]["sample_size"],0)

    def test_pending_counts_only_as_capture_not_settled(self):
        r=audit([pick(status="PENDING")])
        self.assertEqual(r["coverage"]["pregame_quotes_with_valid_frozen_proxy"],1)
        self.assertEqual(r["overall"]["sample_size"],0)

    def test_push_and_out_of_range_probability_excluded(self):
        r=audit([pick(actual=20.5),pick(player_id="2",combined_probability_proxy_estimate=1.2)])
        self.assertEqual(r["overall"]["sample_size"],0)

    def test_pending_age_is_not_equated_with_final_boxscore(self):
        rows = [pick(status="PENDING", player_id="a", event_start="2026-11-08T00:00:00Z"),
                pick(status="PENDING", player_id="b", event_start="2026-11-07T22:00:00Z"),
                pick(status="PENDING", player_id="c", captured_at="2026-11-07T17:00:00Z", event_start="2026-11-07T18:00:00Z"),
                pick(player_id="d", combined_probability_proxy_estimate=None)]
        r = audit(rows, now="2026-11-07T23:00:00Z")
        diag = r["pending_diagnostics"]["counts"]
        self.assertEqual(diag["before_tipoff"], 1)
        self.assertEqual(diag["tipped_off_under_two_hours"], 1)
        self.assertEqual(diag["past_two_hours_unsettled"], 1)
        self.assertEqual(diag["settled_without_proxy"], 1)
        self.assertEqual(r["overall"]["sample_size"], 0)

    def test_full_pregame_capture_to_verified_final_to_confidence_audit(self):
        from iphone_bot.paper_pick_pipeline import snapshot, settle
        market = {
            "player": "Sample Player", "player_id": "123", "team": "BOS",
            "game": "Boston Celtics @ Miami Heat",
            "start": "2026-11-13T00:30:00Z", "stat": "PTS",
            "projection": 26, "combined_projection": 25, "combined_model_count": 2,
            "book_quotes": [{"name": "FanDuel", "line": 22.5,
                             "over": -110, "under": -110,
                             "over_model_probability": .93,
                             "under_model_probability": .07}]
        }
        frozen = snapshot([market], "2026-11-12T20:00:00Z")
        self.assertEqual(len(frozen), 1)
        self.assertEqual(frozen[0]["combined_probability_proxy_estimate"], .93)
        before = audit(frozen, now="2026-11-12T21:00:00Z")
        self.assertEqual(before["overall"]["sample_size"], 0)
        self.assertEqual(before["coverage"]["pregame_quotes_with_valid_frozen_proxy"], 1)
        final = {"player": "Sample Player", "team": "BOS", "opponent": "MIA",
                 "date": "2026-11-12", "PTS": 25, "REB": 4, "AST": 2,
                 "PRA": 31, "MIN": 32, "source": "NBA_CDN_FINAL",
                 "final_confirmed": True, "source_game_id": "0022600030"}
        graded = settle(frozen, [final], "2026-11-13T03:00:00Z")
        self.assertEqual(graded[0]["status"], "SETTLED")
        after = audit(graded, now="2026-11-13T03:01:00Z")
        self.assertEqual(after["overall"]["sample_size"], 1)
        self.assertEqual(after["high_confidence_90_plus"]["wins"], 1)
        self.assertFalse(after["calibrated"])

    def test_unconfirmed_or_mismatched_final_does_not_create_grades(self):
        from iphone_bot.paper_pick_pipeline import snapshot, settle
        market = {
            "player": "Sample Player", "player_id": "123", "team": "BOS",
            "game": "Boston Celtics @ Miami Heat",
            "start": "2026-11-13T00:30:00Z", "stat": "AST",
            "projection": 6, "combined_projection": 6, "combined_model_count": 2,
            "book_quotes": [{"name": "FanDuel", "line": 4.5,
                             "over": -110, "under": -110,
                             "over_model_probability": .85,
                             "under_model_probability": .15}]
        }
        frozen = snapshot([market], "2026-11-12T20:00:00Z")
        final = {"player": "Sample Player", "team": "BOS", "opponent": "MIA",
                 "date": "2026-11-12", "PTS": 10, "REB": 3, "AST": 6,
                 "PRA": 19, "MIN": 31, "source": "NBA_CDN_FINAL",
                 "final_confirmed": False, "source_game_id": "0022600030"}
        self.assertEqual(settle(frozen, [final], "2026-11-13T03:00:00Z")[0]["status"], "PENDING")
        final["final_confirmed"] = True
        final["opponent"] = "NYK"
        self.assertEqual(settle(frozen, [final], "2026-11-13T03:00:00Z")[0]["status"], "PENDING")
        self.assertEqual(audit(frozen)["overall"]["sample_size"], 0)

    def test_single_date_large_sample_never_ready(self):
        r=audit([pick(player_id=str(i)) for i in range(1000)])
        self.assertEqual(r["overall"]["sample_size"],1000)
        self.assertEqual(r["coverage"]["eligible_distinct_game_dates"],1)
        self.assertFalse(r["ready_to_fit_calibration"])

if __name__=="__main__":
    unittest.main()

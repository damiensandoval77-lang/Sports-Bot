import unittest
from unittest.mock import patch,MagicMock
from urllib.error import HTTPError,URLError
from iphone_bot.paper_pick_pipeline import pipeline_health
from iphone_bot.fetch_current_form import fetch,number

class PipelineHealthTests(unittest.TestCase):
    def record(self,start="2026-11-05T20:00:00Z",status="PENDING"):
        return {"status":status,"event_start":start,
                "captured_at":"2026-11-05T15:00:00Z",
                "player_id":"123","team":"BOS","market":"PTS",
                "bookmaker":"Book","line":20.5}
    def test_pending_recent_matchup_is_not_false_failure(self):
        r=pipeline_health([self.record("2026-11-07T01:00:00Z")],
            {"latest_game_date":"2026-11-05","source_version":"2026-11-06"},
            "2026-11-06T12:00:00Z")
        self.assertEqual(r["status"],"OK_AWAITING_MATCHUPS")
        self.assertEqual(r["pending_past_game_buffer"],0)
    def test_old_ungraded_game_is_explicitly_overdue(self):
        r=pipeline_health([self.record()],
            {"latest_game_date":"2026-11-06"},
            "2026-11-08T21:00:00Z")
        self.assertEqual(r["pending_past_game_buffer"],1)
        self.assertEqual(r["pending_over_48_hours"],1)
        self.assertEqual(r["status"],"OVERDUE_UNSETTLED_PICKS")
    def test_5_hour_game_buffer(self):
        r=pipeline_health([self.record()],
            {"latest_game_date":"2026-11-05"},"2026-11-06T00:45:00Z")
        self.assertEqual(r["pending_past_game_buffer"],0)
    def test_missing_source_metadata_not_called_fresh(self):
        r=pipeline_health([self.record()],"no source","2026-11-08T21:00:00Z")
        self.assertEqual(r["status"],"NO_VALIDATED_BOXSCORE_SOURCE")

class GameLogFetchTests(unittest.TestCase):
    def test_nonfinite_numbers_rejected(self):
        for value in ("NaN","inf","-inf","-4",""):
            self.assertIsNone(number(value))
    def test_transient_source_retries_then_succeeds(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b"game logs"
        with patch("iphone_bot.fetch_current_form.urllib.request.urlopen",
                   side_effect=[URLError("temporary"),URLError("temporary"),response]) as open_url,patch("iphone_bot.fetch_current_form.time.sleep") as sleep:
            self.assertEqual(fetch("https://example.test/log.csv"),b"game logs")
            self.assertEqual(open_url.call_count,3)
            self.assertEqual(sleep.call_count,2)
    def test_fatal_not_found_does_not_retry(self):
        error=HTTPError("https://example.test/missing",404,"missing",{},None)
        with patch("iphone_bot.fetch_current_form.urllib.request.urlopen",side_effect=error) as open_url:
            with self.assertRaises(HTTPError):fetch("https://example.test/missing")
            self.assertEqual(open_url.call_count,1)

if __name__=="__main__":unittest.main()

import json
import unittest
from iphone_bot.merge_nba_player_boxscore_publish import merge,parse

def snap(time,status="OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",games=None):
    return json.dumps({"status":status,"captured_at":time,"date_eastern":"2026-11-10",
                       "games":[] if games is None else games})

class SafeBoxscorePublicationTests(unittest.TestCase):
    def test_repairs_specific_trailing_literal_newline(self):
        prior=snap("2026-11-10T00:03:00Z",games=[{"id":"1"}])+r"\n"
        incoming=snap("2026-11-10T00:05:00Z",games=[{"id":"1"},{"id":"2"}])
        result=merge(prior,incoming)
        self.assertEqual(len(result["games"]),2)
    def test_malformed_json_other_than_legacy_suffix_fails_closed(self):
        with self.assertRaises(json.JSONDecodeError):
            merge('{"games":[]}}',snap("2026-11-10T00:05:00Z"))
    def test_previous_newer_snapshot_cannot_be_overwritten(self):
        p=snap("2026-11-10T01:00:00Z",games=[{"id":"1"}])
        n=snap("2026-11-10T00:05:00Z",games=[{"id":"2"}])
        self.assertEqual(merge(p,n)["games"][0]["id"],"1")
    def test_no_empty_or_pregame_overwrite_of_verified_live_box(self):
        p=snap("2026-11-10T00:03:00Z",games=[{"id":"1"}])
        empty=snap("2026-11-10T00:06:00Z")
        pre=snap("2026-11-10T00:07:00Z","WAITING_FOR_SCHEDULED_TIPOFF")
        self.assertEqual(len(merge(p,empty)["games"]),1)
        self.assertEqual(len(merge(p,pre)["games"]),1)
    def test_incoming_json_requires_schema_and_utc(self):
        with self.assertRaisesRegex(ValueError,"INCOMING_TIMESTAMP_INVALID"):
            merge(None,json.dumps({"games":[],"captured_at":"invalid"}))
        with self.assertRaisesRegex(ValueError,"INVALID_SCHEMA"):
            merge(None,json.dumps({"captured_at":"2026-11-10T00:00:00Z"}))
    def test_legacy_committed_file_only_has_known_repairable_suffix(self):
        from pathlib import Path
        src=Path(__file__).resolve().parents[2]/"docs/nba_player_tracking_independent.json"
        payload=parse(src.read_text(),allow_legacy_suffix=True)
        self.assertIsInstance(payload["games"],list)
if __name__=="__main__":unittest.main()

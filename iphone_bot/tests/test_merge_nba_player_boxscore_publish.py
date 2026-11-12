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
    def test_partial_live_refresh_preserves_all_previous_game_rows(self):
        previous=snap("2026-11-10T00:20:00Z",games=[
            {"id":"1","game":"BOS @ NYK","state":"in",
             "observed_at":"2026-11-10T00:20:00Z",
             "player_rows":[{"player":"A","PTS":10}]},
            {"id":"2","game":"UTA @ MIA","state":"in",
             "observed_at":"2026-11-10T00:20:00Z",
             "player_rows":[{"player":"B","PTS":20}]}])
        latest=snap("2026-11-10T00:25:00Z","PARTIAL_NBA_PLAYER_BOXSCORES",games=[
            {"id":"1","game":"BOS @ NYK","state":"in",
             "observed_at":"2026-11-10T00:25:00Z",
             "player_rows":[{"player":"A","PTS":16}]}])
        result=merge(previous,latest)
        by_id={g["id"]:g for g in result["games"]}
        self.assertEqual(len(result["games"]),2)
        self.assertEqual(by_id["1"]["player_rows"][0]["PTS"],16)
        self.assertEqual(by_id["2"]["player_rows"][0]["PTS"],20)
        self.assertEqual(by_id["2"]["observed_at"],"2026-11-10T00:20:00Z")
        self.assertEqual(result["status"],"PARTIAL_NBA_PLAYER_BOXSCORES")
        self.assertFalse(result["coverage"]["complete"])
        self.assertEqual(result["coverage"]["retained_prior_game_count"],1)

    def test_older_game_observation_never_replaces_newer_stored_totals(self):
        previous=snap("2026-11-10T00:20:00Z",games=[
            {"id":"1","game":"BOS @ NYK","state":"in",
             "observed_at":"2026-11-10T00:20:00Z",
             "player_rows":[{"PTS":19}]}])
        newest=snap("2026-11-10T00:30:00Z",games=[
            {"id":"1","game":"BOS @ NYK","state":"in",
             "observed_at":"2026-11-10T00:19:00Z",
             "player_rows":[{"PTS":14}]}])
        result=merge(previous,newest)
        self.assertEqual(result["games"][0]["player_rows"][0]["PTS"],19)

    def test_final_game_cannot_revert_to_in_progress(self):
        previous=snap("2026-11-10T00:20:00Z",games=[
            {"id":"1","game":"BOS @ NYK","state":"post",
             "observed_at":"2026-11-10T00:20:00Z",
             "player_rows":[{"PTS":100}]}])
        new=snap("2026-11-10T00:30:00Z",games=[
            {"id":"1","game":"BOS @ NYK","state":"in",
             "observed_at":"2026-11-10T00:30:00Z",
             "player_rows":[{"PTS":65}]}])
        self.assertEqual(merge(previous,new)["games"][0]["player_rows"][0]["PTS"],100)

    def test_same_matchup_with_different_official_game_id_fails_closed(self):
        old=snap("2026-11-10T00:20:00Z",games=[
            {"id":"1","game":"BOS @ NYK","player_rows":[{"PTS":9}]}])
        new=snap("2026-11-10T00:30:00Z",games=[
            {"id":"2","game":"BOS @ NYK","player_rows":[{"PTS":11}]}])
        with self.assertRaisesRegex(ValueError,"GAME_ID_MISMATCH"):
            merge(old,new)

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

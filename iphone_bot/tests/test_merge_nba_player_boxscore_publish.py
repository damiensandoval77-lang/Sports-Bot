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
    def test_newer_partial_game_does_not_erase_other_verified_game(self):
        old=json.dumps({"status":"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:10:00Z","date_eastern":"2026-11-10",
          "coverage":{"observed_game_count":2,"active_or_final_count":2,"complete":True},
          "games":[
            {"id":"101","game":"Bucks @ Knicks","state":"in",
             "observed_at":"2026-11-11T01:10:00Z","player_rows":[{"player":"A","PTS":14}]},
            {"id":"102","game":"Celtics @ 76ers","state":"in",
             "observed_at":"2026-11-11T01:10:00Z","player_rows":[{"player":"B","PTS":23}]}]})
        new=json.dumps({"status":"PARTIAL_NBA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:15:00Z","date_eastern":"2026-11-10",
          "coverage":{"observed_game_count":1,"active_or_final_count":2,"complete":False},
          "games":[{"id":"101","game":"Bucks @ Knicks","state":"in",
                    "observed_at":"2026-11-11T01:15:00Z",
                    "player_rows":[{"player":"A","PTS":17}]}]})
        result=merge(old,new)
        self.assertEqual(len(result["games"]),2)
        players={g["id"]:g["player_rows"][0]["PTS"] for g in result["games"]}
        self.assertEqual(players,{"101":17,"102":23})
        self.assertEqual(result["status"],"PARTIAL_NBA_PLAYER_BOXSCORES")
        self.assertFalse(result["coverage"]["complete"])
        self.assertEqual(result["preserved_prior_game_observations"],1)
        self.assertEqual(result["games"][1]["observed_at"],"2026-11-11T01:10:00Z")

    def test_older_game_observation_cannot_replace_newer_even_when_wrapper_is_new(self):
        old=json.dumps({"status":"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:15:00Z","date_eastern":"2026-11-10",
          "games":[{"id":"101","game":"Bucks @ Knicks","state":"in",
            "observed_at":"2026-11-11T01:15:00Z",
            "player_rows":[{"player":"A","PTS":17}]}]})
        incoming=json.dumps({"status":"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:20:00Z","date_eastern":"2026-11-10",
          "games":[{"id":"101","game":"Bucks @ Knicks","state":"in",
            "observed_at":"2026-11-11T01:08:00Z",
            "player_rows":[{"player":"A","PTS":4}]}]})
        result=merge(old,incoming)
        self.assertEqual(result["games"][0]["player_rows"][0]["PTS"],17)
        self.assertEqual(result["games"][0]["observed_at"],"2026-11-11T01:15:00Z")
        self.assertEqual(result["status"],"PARTIAL_NBA_PLAYER_BOXSCORES")

    def test_partial_boxscore_without_players_never_zeros_existing_totals(self):
        old=json.dumps({"status":"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:10:00Z","date_eastern":"2026-11-10",
          "games":[{"id":"101","game":"Bucks @ Knicks","state":"in",
            "observed_at":"2026-11-11T01:10:00Z",
            "player_rows":[{"player":"A","PTS":19}]}]})
        new=json.dumps({"status":"PARTIAL_NBA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:12:00Z","date_eastern":"2026-11-10",
          "games":[{"id":"101","game":"Bucks @ Knicks","state":"in",
            "observed_at":"2026-11-11T01:12:00Z","player_rows":[]}]})
        r=merge(old,new)
        self.assertEqual(r["games"][0]["player_rows"][0]["PTS"],19)
        self.assertFalse(r["coverage"]["complete"])

    def test_mismatched_same_game_id_fails_without_overwrite(self):
        old=json.dumps({"status":"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:10:00Z","date_eastern":"2026-11-10",
          "games":[{"id":"101","game":"Bucks @ Knicks","player_rows":[{"PTS":19}]}]})
        new=json.dumps({"status":"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:15:00Z","date_eastern":"2026-11-10",
          "games":[{"id":"101","game":"Celtics @ 76ers","player_rows":[{"PTS":23}]}]})
        with self.assertRaisesRegex(ValueError,"GAME_IDENTITY_CONFLICT"):
            merge(old,new)

    def test_new_eastern_slate_does_not_import_yesterdays_players(self):
        old=json.dumps({"status":"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-11T01:00:00Z","date_eastern":"2026-11-10",
          "games":[{"id":"101","game":"Bucks @ Knicks","player_rows":[{"PTS":19}]}]})
        new=json.dumps({"status":"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
          "captured_at":"2026-11-12T01:00:00Z","date_eastern":"2026-11-11",
          "games":[{"id":"102","game":"Celtics @ 76ers","player_rows":[{"PTS":10}]}]})
        result=merge(old,new)
        self.assertEqual([g["id"] for g in result["games"]],["102"])

    def test_legacy_committed_file_only_has_known_repairable_suffix(self):
        from pathlib import Path
        src=Path(__file__).resolve().parents[2]/"docs/nba_player_tracking_independent.json"
        payload=parse(src.read_text(),allow_legacy_suffix=True)
        self.assertIsInstance(payload["games"],list)
if __name__=="__main__":unittest.main()

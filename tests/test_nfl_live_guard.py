import unittest
from scripts.guard_nfl_live_snapshot import should_publish


def snapshot(when="2026-11-10T02:30:00Z",status="ok",count=4,game_state="in"):
    return {"season":2026,"checked_at":when,"status":status,"errors":[],
            "games":[{"game_id":"2026_09_BUF_MIN","status":game_state,
                      "players":[{"player":f"p{i}","team":"BUF","stats":{"PASS_ATT":i}}
                                 for i in range(count)]}]}


class SnapshotGuardTests(unittest.TestCase):
    def test_newer_good_with_same_or_more_players(self):
        ok,why=should_publish(snapshot(),snapshot("2026-11-10T02:35:00Z",count=5))
        self.assertTrue(ok)
        self.assertEqual(why,"verified_newer_snapshot")

    def test_older_fetch_never_overwrites(self):
        self.assertEqual(should_publish(snapshot(),snapshot("2026-11-10T02:25:00Z"))[1],
                         "older_or_duplicate_snapshot")

    def test_missing_players_does_not_wipe_boxscore(self):
        self.assertEqual(should_publish(snapshot(),snapshot("2026-11-10T02:35:00Z",count=2))[1],
                         "player_coverage_regressed")

    def test_provider_partial_never_replaces_verified(self):
        self.assertEqual(should_publish(snapshot(),snapshot("2026-11-10T02:35:00Z",status="partial_or_unavailable"))[1],
                         "partial_provider_response")

    def test_earlier_game_status_not_downgraded(self):
        self.assertEqual(should_publish(snapshot(),snapshot("2026-11-10T02:35:00Z",game_state="pre"))[1],
                         "status_regressed")

    def test_final_game_does_not_revert(self):
        self.assertEqual(should_publish(snapshot(game_state="post"),snapshot("2026-11-10T02:35:00Z"))[1],
                         "final_status_regressed")

    def test_no_active_games_cannot_remove_valid_history(self):
        update=snapshot("2026-11-10T02:35:00Z")
        update["games"]=[]
        update["status"]="no_active_window"
        self.assertEqual(should_publish(snapshot(),update)[1],
                         "empty_or_no_active_game_snapshot")

    def test_invalid_timestamp_fails_closed(self):
        update=snapshot()
        update["checked_at"]="bad timestamp"
        self.assertEqual(should_publish(None,update)[1],"invalid_new_snapshot")

    def test_initial_good_snapshot_can_publish(self):
        self.assertEqual(should_publish(None,snapshot())[0],True)


if __name__=="__main__":
    unittest.main()

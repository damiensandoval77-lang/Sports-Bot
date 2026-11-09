import datetime as dt
import unittest
from iphone_bot.refresh_independent_scoreboard import snapshot

UTC=dt.timezone.utc
NOW=dt.datetime(2026,11,9,12,tzinfo=UTC)
DAY=dt.date(2026,11,9)

def event(id="123"):
    return {"id":id,"date":"2026-11-09T23:00:00Z",
            "competitions":[{"competitors":[
                {"homeAway":"home","team":{"displayName":"Home","abbreviation":"HOM"},"score":"0"},
                {"homeAway":"away","team":{"displayName":"Away","abbreviation":"AWY"},"score":"0"}]}],
            "status":{"type":{"state":"pre"}}}

class IndependentScoreboardTests(unittest.TestCase):
    def test_fetches_schedule_and_labels_not_odds(self):
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW)
        self.assertEqual(r["total_games"],1)
        self.assertEqual(r["status"],"OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES")
        self.assertFalse(r["is_sportsbook_feed"])
        self.assertFalse(r["is_prizepicks_feed"])

    def test_no_games_is_valid_when_provider_responds(self):
        r=snapshot([DAY],reader=lambda _: [],now=NOW)
        self.assertEqual(r["total_games"],0)
        self.assertIsNone(r["error"])

    def test_failure_keeps_old_capture_time(self):
        prior={"generated_at":"2026-11-09T10:00:00+00:00","games":[{"id":"old"}],"total_games":1}
        def fail(_): raise OSError("network unavailable")
        r=snapshot([DAY],reader=fail,now=NOW,previous=prior)
        self.assertEqual(r["status"],"STALE_UPSTREAM_ERROR")
        self.assertEqual(r["generated_at"],prior["generated_at"])
        self.assertEqual(r["games"],prior["games"])

    def test_failure_without_history_never_marks_fresh(self):
        def fail(_): raise TimeoutError("timeout")
        r=snapshot([DAY],reader=fail,now=NOW)
        self.assertEqual(r["status"],"UNAVAILABLE_UPSTREAM_ERROR")
        self.assertIsNone(r["generated_at"])

    def test_duplicate_dates_fail_closed(self):
        r=snapshot([DAY,DAY],reader=lambda _: [event()],now=NOW)
        self.assertEqual(r["status"],"UNAVAILABLE_UPSTREAM_ERROR")


    def test_empty_provider_response_rejected_if_schedule_has_games(self):
        baseline={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat()}]}
        r=snapshot([DAY],reader=lambda _: [],now=NOW,schedule=baseline)
        self.assertEqual(r["status"],"UNAVAILABLE_UPSTREAM_ERROR")
        self.assertIsNone(r["generated_at"])

    def test_provider_missing_one_matchup_retains_previous(self):
        baseline={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat()},
                           {"game":"Other @ Other Home","date_eastern":DAY.isoformat()}]}
        prior={"generated_at":"2026-11-09T10:00:00+00:00",
               "games":[{"id":"saved"}],"total_games":1}
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW,
                   previous=prior,schedule=baseline)
        self.assertEqual(r["status"],"STALE_UPSTREAM_ERROR")
        self.assertEqual(r["generated_at"],prior["generated_at"])

    def test_complete_provider_matches_known_slate(self):
        baseline={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat()}]}
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW,schedule=baseline)
        self.assertEqual(r["total_games"],1)
        self.assertEqual(r["status"],"OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES")

    def test_incomplete_schedule_not_used_as_coverage_assertion(self):
        baseline={"coverage_complete":False,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Other @ Other Home","date_eastern":DAY.isoformat()}]}
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW,schedule=baseline)
        self.assertEqual(r["status"],"OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES")

if __name__=="__main__":
    unittest.main()

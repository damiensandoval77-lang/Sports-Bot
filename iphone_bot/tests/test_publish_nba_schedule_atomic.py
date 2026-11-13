import datetime as dt
import unittest
from iphone_bot.publish_nba_schedule_atomic import stage
from iphone_bot.tests.test_season_schedule_baseline import baseline, NOW
from iphone_bot.season_schedule_baseline import ET

class AtomicSchedulePublishTests(unittest.TestCase):
    def test_stale_zero_game_refresh_never_erases_published_season(self):
        master=baseline()
        current={"generated_at":"2026-11-10T18:20:00+00:00","status":"THIRD_PARTY_NBA_SCHEDULE_ONLY",
                 "coverage_complete":True,"games":[],"total_games":0}
        candidate={"generated_at":"2026-11-10T18:30:00+00:00","status":"SCHEDULE_UNAVAILABLE",
                   "coverage_complete":False,"games":[],"total_games":0}
        result,persisted=stage(candidate,master,current,master,now=NOW)
        expected=sum(g["date_eastern"] in {"2026-11-10","2026-11-11"} for g in master["games"])
        self.assertEqual(result["total_games"],expected)
        self.assertTrue(result["coverage_complete"])
        self.assertEqual(persisted["total_games"],1050)
        self.assertGreater(result["baseline_recovered"],0)

    def test_newer_trusted_score_is_retained_for_matching_game(self):
        master=baseline()
        today=NOW.astimezone(ET).date().isoformat()
        original=next(g for g in master["games"] if g["date_eastern"]==today)
        observed={**original,"game_state":"in","home_score":86,"away_score":79}
        current={"generated_at":"2026-11-10T18:30:00+00:00",
                 "coverage_complete":True,"games":[observed]}
        old_candidate={"generated_at":"2026-11-10T17:30:00+00:00",
                       "status":"SCHEDULE_UNAVAILABLE","games":[]}
        result,_=stage(old_candidate,master,current,master,now=NOW)
        found=next(g for g in result["games"] if g["id"]==original["id"])
        self.assertEqual(found["home_score"],86)
        self.assertEqual(found["game_state"],"in")

    def test_unknown_or_corrupt_season_cannot_replace_verifiable_master(self):
        master=baseline()
        corrupt={"status":"INVALID","games":[]}
        result,persisted=stage({},corrupt,{},master,now=NOW)
        self.assertEqual(persisted["status"],master["status"])
        self.assertTrue(result["coverage_complete"])

    def test_two_invalid_season_sources_refuse_to_publish(self):
        with self.assertRaises(ValueError):
            stage({},{"status":"UNKNOWN"},{},{"status":"UNKNOWN"},now=NOW)

if __name__=="__main__":
    unittest.main()

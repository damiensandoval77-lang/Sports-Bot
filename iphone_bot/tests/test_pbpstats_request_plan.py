"""Offline request builder must never fetch provider data."""
import unittest
from iphone_bot.pbpstats_request_plan import TEAM_IDS,request_plan

class RequestPlanTests(unittest.TestCase):
    def test_canonical_wowy_on_floor_and_off_floor(self):
        p=request_plan("201939","203110","GSW")
        self.assertEqual(p["status"],"REQUEST_PLAN_ONLY_NETWORK_DISABLED")
        self.assertEqual(p["requests"]["with"]["0Exactly1OnFloor"],"201939")
        self.assertEqual(p["requests"]["with"]["1Exactly1OnFloor"],"203110")
        self.assertEqual(p["requests"]["without"]["1Exactly1OffFloor"],"203110")
        self.assertNotIn("1Exactly1OnFloor",p["requests"]["without"])
        self.assertEqual(p["requests"]["with"]["TeamId"],"1610612744")
        self.assertTrue(p["requires_verified_game_date_cutoff"])
        self.assertFalse(p["response_mapping_verified"])
    def test_provider_supported_date_range_prevents_post_tip_season_leakage(self):
        plan=request_plan("201939","203110","GSW",cutoff_date="2026-11-06")
        for group in ("with","without"):
            self.assertEqual(plan["requests"][group]["FromDate"],"2026-07-01")
            self.assertEqual(plan["requests"][group]["ToDate"],"2026-11-06")
        self.assertTrue(plan["historical_date_filter_applied"])
        self.assertFalse(request_plan("201939","203110","GSW")["historical_date_filter_applied"])
        for invalid in ("2026-05-03","2027-07-01","not-a-date"):
            with self.assertRaises(ValueError):
                request_plan("201939","203110","GSW",cutoff_date=invalid)

    def test_all_nba_teams_and_invalid_ids(self):
        self.assertEqual(len(TEAM_IDS),30)
        self.assertEqual(len(set(TEAM_IDS.values())),30)
        for p,t,team in (("x","22","BOS"),("22","22","BOS"),
                         ("2","3","FAKE")):
            with self.assertRaises(ValueError):
                request_plan(p,t,team)
        with self.assertRaises(ValueError):
            request_plan("1","2","BOS",season="2024-25")

if __name__=="__main__":unittest.main()

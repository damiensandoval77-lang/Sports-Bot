import datetime as dt
import unittest
from iphone_bot.fetch_hoopr_nba_schedule import apply_official_evidence

def stale_seven_games():
    opponents=[("CLE","CHA"),("LAL","ATL"),("MEM","TOR"),
               ("IND","DAL"),("DEN","HOU"),("SAS","PHX"),("NOP","GSW")]
    rows=[]
    for a,b in opponents:
        rows.append({"id":a+b,"away_abbreviation":a,"home_abbreviation":b,
                     "date_eastern":"2026-11-09","game":"Away @ Home",
                     "start":"2026-11-10T01:00:00+00:00","game_state":"pre"})
    return {"status":"THIRD_PARTY_NBA_SCHEDULE_ONLY",
            "source":"sportsdataverse hoopR ESPN-derived season schedule",
            "dates_eastern":["2026-11-09","2026-11-10"],
            "games":rows,"total_games":7,"coverage_complete":True}

class HooprSchedulePublishProtectionTests(unittest.TestCase):
    def test_seven_game_hoopr_is_fixed_inside_fetcher_before_publish(self):
        repaired=apply_official_evidence(stale_seven_games())
        self.assertEqual(repaired["total_games"],8)
        self.assertTrue(repaired["coverage_complete"])
        self.assertIn("NBA.com verified fixtures",repaired["source"])
        self.assertEqual(
            [g["game"] for g in repaired["games"] if g["away_abbreviation"]=="WAS"],
            ["Washington Wizards @ Detroit Pistons"])
        self.assertEqual(repaired["official_fixture_reconciliation"]
                         ["verified_daily_counts"]["2026-11-09"]["observed"],8)

    def test_repeated_scheduled_publish_cannot_remove_verified_game(self):
        first=apply_official_evidence(stale_seven_games())
        second=apply_official_evidence(first)
        self.assertEqual(second["total_games"],8)
        self.assertEqual(second["official_fixture_reconciliation"]["newly_recovered"],[])

    def test_future_day_does_not_reintroduce_old_fixture(self):
        later=stale_seven_games()
        later["dates_eastern"]=["2026-11-10","2026-11-11"]
        later["games"]=[]
        later["total_games"]=0
        current=apply_official_evidence(later)
        self.assertEqual(current["total_games"],0)
        self.assertNotIn("2026-11-09",
                         current["official_fixture_reconciliation"]["verified_daily_counts"])

if __name__=="__main__":
    unittest.main()

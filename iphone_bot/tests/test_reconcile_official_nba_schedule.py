import copy
import json
import unittest
from pathlib import Path
from iphone_bot.reconcile_official_nba_schedule import reconcile, FIX

SOURCE=json.loads(FIX.read_text())
def slate():
    rows=[
       {"id":str(i),"game":"Away"+str(i)+" @ Home"+str(i),
        "away":"Away"+str(i),"home":"Home"+str(i),
        "away_abbreviation":a,"home_abbreviation":b,
        "date_eastern":"2026-11-09","start":"2026-11-10T01:00:00Z","game_state":"pre"}
        for i,(a,b) in enumerate([
         ("CLE","CHA"),("LAL","ATL"),("MEM","TOR"),("IND","DAL"),
         ("DEN","HOU"),("SAS","PHX"),("NOP","GSW")],start=1)]
    return {"games":rows,"total_games":7,"coverage_complete":True,
            "source":"ESPN-derived source","dates_eastern":["2026-11-09"]}
class OfficialSlateTests(unittest.TestCase):
    def test_workflow_explicitly_dispatches_fresh_scoreboard(self):
        workflow=(Path(__file__).resolve().parents[2]/
                  ".github/workflows/official_nba_fixture_reconciliation.yml").read_text()
        self.assertIn("actions: write",workflow)
        self.assertIn("gh workflow run independent_scoreboard_refresh.yml --ref main",workflow)
        self.assertIn("github.event_name != 'pull_request'",workflow)

    def test_seven_game_false_complete_recovered_to_eight(self):
        result=reconcile(slate(),SOURCE)
        self.assertEqual(result["total_games"],8)
        self.assertEqual(result["official_fixture_reconciliation"]["verified_daily_counts"]["2026-11-09"]["official_expected"],8)
        recovered=result["official_fixture_reconciliation"]["newly_recovered"]
        self.assertEqual([x["game"] for x in recovered],
                         ["Washington Wizards @ Detroit Pistons"])
        self.assertTrue(result["coverage_complete"])

    def test_missing_expected_game_never_marked_complete(self):
        modified=copy.deepcopy(SOURCE)
        modified["fixtures"]=[]
        with self.assertRaisesRegex(ValueError,"slate count mismatch"):
            reconcile(slate(),modified)

    def test_idempotence_same_official_fixture_no_duplicate(self):
        first=reconcile(slate(),SOURCE)
        second=reconcile(first,SOURCE)
        self.assertEqual(second["total_games"],8)
        self.assertEqual(second["official_fixture_reconciliation"]["newly_recovered"],[])

    def test_false_domain_or_non_official_game_id_rejected(self):
        for key,value in [("official_url","https://example.com/game/0022600205"),
                          ("id","FAKE"),("home_abbreviation","ZZZ")]:
            modified=copy.deepcopy(SOURCE)
            modified["fixtures"][0][key]=value
            with self.assertRaises(ValueError):
                reconcile(slate(),modified)

    def test_conflicting_start_time_not_silently_overwritten(self):
        altered=slate()
        altered["games"].append({**SOURCE["fixtures"][0],
            "start":"2026-11-10T02:00:00Z"})
        with self.assertRaisesRegex(ValueError,"Conflicting NBA tip"):
            reconcile(altered,SOURCE)

if __name__=="__main__":
    unittest.main()

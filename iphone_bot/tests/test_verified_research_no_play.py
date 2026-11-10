"""Historical confirmed NBA DNPs never become losses or invented minutes."""
import datetime as dt
import unittest
from iphone_bot.verified_research_no_play import evidence_map,match,exclude_pending
from iphone_bot.assist_v2_shadow_capture import grade,summary
from iphone_bot.minutes_scenario_validation import settle,report

NOW=dt.datetime(2026,11,10,15,tzinfo=dt.timezone.utc)
GAMES=[
 ("Jarrett Allen","1628386","CLE","Philadelphia 76ers @ Cleveland Cavaliers","2026-11-07T00:40:00+00:00"),
 ("Desmond Bane","1630217","ORL","Orlando Magic @ Golden State Warriors","2026-11-08T01:40:00+00:00"),
 ("Anthony Davis","203076","WAS","Washington Wizards @ Oklahoma City Thunder","2026-11-08T01:10:00+00:00")
]
def base(which):
    name,pid,team,game,start=GAMES[which]
    return {"status":"PENDING","player":name,"player_id":pid,"team":team,
       "game":game,"event_start":start,"captured_at":"2026-11-06T22:00:00+00:00",
       "baseline_minutes":30.0,"scenario_minutes":33.0}
def assist(which):
    return {**base(which),"market":"AST","line":4.5,"side":"UNDER",
            "american_odds":-110,"baseline_projection":3.8,"v2_projection":3.6,
            "bookmaker":"Sample"}
class VerifiedNoPlayTests(unittest.TestCase):
    def test_only_exact_three_source_confirmed_inactives(self):
        self.assertEqual(len(evidence_map()),3)
        for i in range(3):
            self.assertIsNotNone(match(base(i),now=NOW))
        altered={**base(1),"player_id":"wrong"}
        self.assertIsNone(match(altered,now=NOW))
        self.assertIsNone(match({**base(1),"captured_at":"2026-11-09T00:00:00Z"},now=NOW))
    def test_assist_voids_ten_lines_without_affecting_hit_rate(self):
        rows=[assist(1),assist(2)]
        for _ in range(3):rows.extend([assist(1),assist(2)])
        rows+= [assist(1),assist(2)]
        out=grade(rows,[],now=NOW.isoformat())
        self.assertEqual(len(out),10)
        self.assertTrue(all(x["status"]=="VOID_DNP" and x["result"]=="VOID" for x in out))
        result=summary(out)
        self.assertEqual(result["verified_no_play_voids"],10)
        self.assertEqual(result["pending"],0)
        self.assertEqual(result["settled"],0)
        self.assertIsNone(result["hit_rate"])
    def test_minutes_excludes_three_without_counting_zero_minutes(self):
        rows=settle([base(i) for i in range(3)],[],now=NOW.isoformat())
        self.assertEqual([r["status"] for r in rows],["EXCLUDED_VERIFIED_DNP"]*3)
        x=report(rows,now=NOW.isoformat())
        self.assertEqual(x["verified_dnp_exclusions"],3)
        self.assertEqual(x["settled"],0)
        self.assertEqual(x["pending"],0)
        self.assertEqual(x["accounted_for"],3)
    def test_evidence_unavailable_stays_pending(self):
        unknown={**base(0),"player_id":"unknown"}
        self.assertEqual(exclude_pending([unknown],now=NOW)[0]["status"],"PENDING")
if __name__=="__main__":unittest.main()

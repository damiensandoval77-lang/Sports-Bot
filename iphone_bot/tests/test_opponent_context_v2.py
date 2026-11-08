"""No lookahead, no fake pace/defender impact, fixed research challenger."""
import unittest
from iphone_bot.opponent_context_v2 import games_by_team,matchup,shadow

def games(include_pace=True):
    rows=[]
    for day in range(1,19):
        d=f"2026-10-{day:02d}"
        for team,opp,pts in (("BOS","MIA",12),("MIA","BOS",10)):
            for i in range(8):
                r={"id":f"{team}{i}","date":d,"team":team,"opponent":opp,
                   "PTS":pts,"REB":5,"AST":3,"MIN":25}
                if include_pace:r.update(FGA=10,FTA=3,OREB=2,TOV=2)
                rows.append(r)
    return rows

class OpponentContextV2Tests(unittest.TestCase):
    def test_pace_and_efficiency_from_reciprocal_prior_boxes(self):
        teams=games_by_team(games(),"2026-10-16")
        c=matchup(teams,"BOS","MIA","PTS",["203076"])
        self.assertEqual(c["status"],"PACE_EFFICIENCY_PAST_ONLY")
        self.assertIsNotNone(c["pace_ratio"])
        self.assertGreater(c["relative_factor"],0)
        self.assertFalse(c["individual_defender_impact_applied"])
        self.assertEqual(c["out_defender_ids"],["203076"])
        self.assertAlmostEqual(shadow(20,c),20*c["relative_factor"],places=3)
    def test_no_possession_source_falls_back_not_invents_pace(self):
        teams=games_by_team(games(False),"2026-10-16")
        c=matchup(teams,"BOS","MIA","REB")
        self.assertEqual(c["status"],"DEFENSIVE_TOTALS_PAST_ONLY")
        self.assertIsNone(c["pace_ratio"])
        self.assertIsNone(c["defensive_efficiency_ratio"])
    def test_future_outlier_and_incomplete_opponents_excluded(self):
        base=games()
        a=games_by_team(base,"2026-10-12")
        future={"id":"extra","date":"2026-10-12","team":"MIA","opponent":"BOS",
                "PTS":5000,"REB":5000,"AST":5000,"FGA":1000,"FTA":0,
                "OREB":0,"TOV":0}
        b=games_by_team(base+[future],"2026-10-12")
        self.assertEqual(a,b)
        single=[r for r in base if not(r["date"]=="2026-10-04" and r["team"]=="MIA")]
        c=games_by_team(single,"2026-10-12")
        self.assertEqual(len(c["BOS"]),10)
    def test_insufficient_games_no_fabricated_boost(self):
        c=matchup({},"BOS","MIA","PRA")
        self.assertIsNone(c["relative_factor"])
        self.assertIsNone(shadow(22,c))
        self.assertFalse(c["eligible_for_production"] if "eligible_for_production" in c else False)

if __name__=="__main__":unittest.main()

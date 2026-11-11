import copy
import unittest
from datetime import datetime,timedelta,timezone
from research.paired_positional_holdout import (prepare,make_indexes,
    matchup_projection,evaluate)

ROLE=("PG","SG","SF","PF","C","SG","SF","PF")

def games(count=14):
    result=[]
    for dayno in range(count):
        day=(datetime(2026,10,20,tzinfo=timezone.utc)+timedelta(days=dayno)).date().isoformat()
        for a,b in (("BOS","NYK"),("LAL","CHI")):
            for team,opp in ((a,b),(b,a)):
                for idx,pos in enumerate(ROLE):
                    pts=12+idx+(3 if opp=="NYK" else 0)+dayno%3
                    reb=idx+2
                    ast=idx%5+2
                    result.append({"date":day,"team":team,"opponent":opp,
                        "id":team+str(idx),"position":pos,
                        "PTS":pts,"REB":reb,"AST":ast,"PRA":pts+reb+ast,"MIN":27})
    return result

class PairedHoldoutTests(unittest.TestCase):
    def test_same_cohort_comparison_has_no_production_promotion(self):
        r=evaluate(games(),holdout_days=5,min_opponent=5,min_league=8)
        self.assertFalse(r["production_approved"])
        self.assertFalse(r["probability_calibrated"])
        self.assertGreater(r["paired_markets"]["PTS"]["paired_player_games"],0)
        self.assertEqual(r["paired_markets"]["PTS"]["paired_player_games"],
                         r["paired_markets"]["REB"]["paired_player_games"])

    def test_modifying_target_outcome_cannot_change_target_projection(self):
        original=games()
        clean,_=prepare(original)
        players,allowed=make_indexes(clean)
        row=clean[-1]
        a=matchup_projection(row,players[(row["id"],row["team"])],allowed,"PTS",
                             min_opponent=5,min_league=8)
        altered=copy.deepcopy(original)
        for r in altered:
            if (r["date"],r["team"],r["id"])==(row["date"],row["team"],row["id"]):
                r["PTS"]+=40;r["PRA"]+=40
        clean2,_=prepare(altered)
        p2,allowed2=make_indexes(clean2)
        target=next(x for x in clean2 if (x["date"],x["team"],x["id"])==
            (row["date"],row["team"],row["id"]))
        b=matchup_projection(target,p2[(target["id"],target["team"])],allowed2,"PTS",
                             min_opponent=5,min_league=8)
        self.assertEqual(a,b)

    def test_incomplete_reciprocal_game_rejected(self):
        x=games()
        x=[r for r in x if not (r["date"]=="2026-10-22" and
                                  r["team"]=="NYK" and r["id"] in ("NYK0","NYK1"))]
        clean,issues=prepare(x)
        self.assertFalse(any(r["date"]=="2026-10-22" and r["team"]=="BOS" for r in clean))
        self.assertGreater(issues["partial_reciprocal_box"],0)

    def test_corrupt_game_does_not_form_defense_sample(self):
        x=games()
        x[0]["PRA"]=-1
        clean,issues=prepare(x)
        self.assertFalse(any(r["date"]=="2026-10-20" and r["team"]=="BOS" for r in clean))
        self.assertGreater(issues["corrupt_team_stats"],0)

    def test_no_qualified_opponent_sample_returns_none(self):
        clean,_=prepare(games(5))
        players,allowed=make_indexes(clean)
        row=clean[-1]
        self.assertIsNone(matchup_projection(row,players[(row["id"],row["team"])],
                                            allowed,"PTS",min_opponent=8,min_league=8))

    def test_unknown_position_is_not_inferred(self):
        x=games()
        for r in x:
            if r["id"]=="BOS0":r["position"]="G"
        clean,_=prepare(x)
        players,allowed=make_indexes(clean)
        target=next(r for r in clean if r["id"]=="BOS0" and r["date"]==clean[-1]["date"])
        self.assertIsNone(matchup_projection(target,players[("BOS0","BOS")],allowed,
                                            "PTS",min_opponent=5,min_league=8))

    def test_insufficient_data_returns_explicit_no_cohort(self):
        r=evaluate([],holdout_days=7)
        self.assertEqual(r["status"],"NO_RECIPROCAL_GAME_DATA")
        self.assertFalse(r["production_approved"])

if __name__=="__main__":unittest.main()

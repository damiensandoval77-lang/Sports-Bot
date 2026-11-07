"""Shot-profile research: no retroactive knowledge and valid two/three-point identities."""
import csv
import tempfile
import unittest
from pathlib import Path
from iphone_bot.shot_profile_research import (
    normalized,predict_attempts,predict_points,evaluate,load_history
)


def g(day,team="BOS",id="7",season="2025-26",fga=15,three=6,
      fgm=7,threem=2,fta=5,ftm=4):
    return {"id":id,"date":f"2026-01-{day:02d}","game_id":f"gm-{day}",
            "season":season,"team":team,"MIN":30,"FGA":fga,"FG3A":three,
            "FGM":fgm,"FG3M":threem,"FTA":fta,"FTM":ftm,
            "PTS":2*(fgm-threem)+3*threem+ftm}


class ShotProfileTests(unittest.TestCase):
    def test_two_point_shots_are_total_minus_threes(self):
        obs=normalized(g(1))
        self.assertEqual(obs["FG2A"],9)
        self.assertEqual(obs["FG2M"],5)
        self.assertEqual(obs["PTS"],20)
        self.assertIsNone(normalized(g(1,three=20)))
        bad=g(1);bad["PTS"]=30
        self.assertIsNone(normalized(bad))
        self.assertIsNone(normalized(dict(g(1),FG3M=8)))

    def test_all_attempts_from_only_prior_same_team_games(self):
        history=[g(d) for d in range(1,10)]
        output=predict_attempts(history,"2026-01-10","BOS",30)
        self.assertEqual(output["status"],"SHOT_PROFILE_RESEARCH_UNVALIDATED")
        self.assertAlmostEqual(output["expected_fga"],15)
        self.assertAlmostEqual(output["expected_3pa"],6)
        self.assertAlmostEqual(output["expected_2pa"],9)
        self.assertAlmostEqual(output["three_point_attempt_share"],.4)
        future=g(12,fga=50,three=40)
        wrong_team=g(9,team="MIA",fga=80,three=60)
        unchanged=predict_attempts(history+[future,wrong_team],"2026-01-10","BOS",30)
        self.assertEqual(output,unchanged)
        self.assertFalse(output["live_adjustment_applied"])
        self.assertFalse(output["is_verified_shot_location"])

    def test_point_decomposition_includes_ft_separately(self):
        history=[g(d) for d in range(1,10)]
        result=predict_points(history,"2026-01-10","BOS",30)
        self.assertIsNotNone(result)
        self.assertGreater(result["expected_fta"],0)
        self.assertLess(result["expected_3pa"],result["expected_fga"])
        self.assertAlmostEqual(result["expected_fga"],
                               result["expected_2pa"]+result["expected_3pa"])
        self.assertFalse(result["live_adjustment_applied"])

    def test_evaluation_heldout_no_season_or_team_merging(self):
        records=[]
        for season,year in (("2024-25",2025),("2025-26",2026)):
            for d in range(1,13):
                sample=g(d,season=season)
                sample["date"]=f"{year}-01-{d:02d}"
                sample["game_id"]=f"{season}-{d}"
                records.append(sample)
        result=evaluate(records)
        self.assertEqual(result["earlier_seasons"]["observations"],4)
        self.assertEqual(result["holdout"]["observations"],4)
        self.assertFalse(result["production_adjustment_applied"])
        self.assertFalse(result["injury_usage_change_applied"])
        self.assertEqual(result["shot_location_detail"],"TWO_POINT_VERSUS_THREE_POINT_ONLY")

    def test_archive_conflicts_and_invalid_box_scores(self):
        first=g(1)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"archive.csv"
            fields=("PLAYER_ID","GAME_ID","GAME_DATE","SEASON_ID",
                    "TEAM_ABBREVIATION","MIN","FGA","FG3A","FGM",
                    "FG3M","FTA","FTM","PTS")
            def write(rows):
                with path.open("w",newline="") as file:
                    w=csv.DictWriter(file,fieldnames=fields)
                    w.writeheader()
                    for row in rows:
                        out={key:row[field] for key,field in {
                            "PLAYER_ID":"id","GAME_ID":"game_id","GAME_DATE":"date",
                            "SEASON_ID":"season","TEAM_ABBREVIATION":"team",
                            "MIN":"MIN","FGA":"FGA","FG3A":"FG3A",
                            "FGM":"FGM","FG3M":"FG3M","FTA":"FTA",
                            "FTM":"FTM","PTS":"PTS"}.items()}
                        w.writerow(out)
            write([first,first])
            good,quality=load_history(path)
            self.assertEqual(len(good),1)
            self.assertEqual(quality["duplicate"],1)
            invalid=dict(first,FG3A=50)
            write([first,invalid])
            good,quality=load_history(path)
            self.assertEqual(len(good),1)
            self.assertEqual(quality["invalid_box_score"],1)
            conflicting=dict(first,FG3A=5,FGA=14)
            write([first,conflicting])
            with self.assertRaises(ValueError):
                load_history(path)


if __name__=="__main__":unittest.main()

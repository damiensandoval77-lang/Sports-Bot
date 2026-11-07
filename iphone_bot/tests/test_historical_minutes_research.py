"""Archival quality, past-only rotation context and 2025-26 holdout."""
import csv
import tempfile
import unittest
from pathlib import Path
from iphone_bot.historical_minutes_research import load_archive,evaluate


def sample(season="2025-26",day=1,pid="1",team="BOS",minutes=30,game_id=None):
    yr=int(season[:4])+1
    return {"season":season,"id":str(pid),"game_id":str(game_id or f"{season}-{day}"),
            "date":f"{yr}-01-{day:02d}","team":team,"MIN":minutes}


class HistoricalMinutesTests(unittest.TestCase):
    def archive(self,records):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"archive.csv"
            with path.open("w",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=[
                    "PLAYER_ID","GAME_ID","GAME_DATE","TEAM_ABBREVIATION","MIN","SEASON_ID"])
                writer.writeheader()
                for r in records:
                    writer.writerow({"PLAYER_ID":r["id"],"GAME_ID":r["game_id"],
                        "GAME_DATE":r["date"],"TEAM_ABBREVIATION":r["team"],
                        "MIN":r["MIN"],"SEASON_ID":r["season"]})
            return load_archive(path)

    def test_identical_duplicate_skipped_and_conflict_halts(self):
        a=sample()
        rows,bad=self.archive([a,a])
        self.assertEqual(len(rows),1)
        self.assertEqual(bad["identical_duplicate"],1)
        with self.assertRaises(ValueError):
            self.archive([a,dict(a,MIN=22)])

    def test_bad_dates_and_nonfinite_minutes_rejected(self):
        good=sample()
        wrong=dict(sample(pid="2"),date="2023-01-01")
        nan=dict(sample(pid="3"),MIN="NaN")
        rows,bad=self.archive([good,wrong,nan])
        self.assertEqual(len(rows),1)
        self.assertEqual(bad["wrong_season_date"],1)
        self.assertEqual(bad["missing_or_invalid_minutes"],1)

    def test_2025_26_holdout_and_team_season_reset(self):
        games=[]
        for season in ("2024-25","2025-26"):
            for d in range(1,15):
                for p in range(5):
                    games.append(sample(season,d,str(p),minutes=30 if d<13 else 33,
                                        game_id=f"{season}-{d}"))
        result=evaluate(games)
        self.assertEqual(result["earlier_seasons"]["observations"],30)
        self.assertEqual(result["holdout"]["observations"],30)
        self.assertEqual(result["holdout_season"],"2025-26")
        self.assertFalse(result["production_adjustment_applied"])
        self.assertFalse(result["injury_effect_claimed"])

    def test_trade_requires_eight_prior_games_on_new_team(self):
        games=[sample(day=d,pid="8",team="BOS") for d in range(1,10)]
        games += [sample(day=d,pid="8",team="MIA") for d in range(10,15)]
        r=evaluate(games)
        self.assertEqual(r["holdout"]["observations"],1)

    def test_future_outcomes_do_not_change_past_rotation_inputs(self):
        games=[sample(day=d,pid="7",minutes=25) for d in range(1,12)]
        same=evaluate(games)["holdout"]
        future=games+[sample(day=12,pid="7",minutes=50)]
        full=evaluate(future)["holdout"]
        self.assertEqual(same["observations"],3)
        self.assertEqual(full["observations"],4)
        self.assertEqual(same["baseline_mae"],0)
        self.assertEqual(same["candidate_mae"],0)
        self.assertEqual(full["observations"]-same["observations"],1)


if __name__=="__main__":unittest.main()

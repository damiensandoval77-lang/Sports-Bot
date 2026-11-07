"""Independent season replication must retain the frozen research boundary."""
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import pyarrow as pa
import pyarrow.parquet as pq
from iphone_bot import defender_v3_replication as replication
from iphone_bot.defender_v3_points import load_player_games,load_defender_games


class CrossSeasonTests(unittest.TestCase):
    def test_only_selected_2024_season_boxscores_are_eligible(self):
        raw=[]
        for year in (2024,2025):
            raw.append({"player_id":10,"game_id":f"002{str(year)[2:]}00001",
                "game_date":f"{year}-11-04","team":"BOS","opponent":"NYK",
                "minutes":30.,"pts":20,"fgm":7,"fga":15,
                "fg3m":2,"fg3a":6,"ftm":4,"fta":5})
        rows=load_player_games(pa.Table.from_pylist(raw),season_start=2024)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["date"],"2024-11-04")

    def test_replication_failure_is_explicit_and_cannot_promote(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(replication,"REPORT",Path(d)/"status.json"):
                result=replication.run(Path(d)/"missing_matchups.parquet",
                                       Path(d)/"missing_boxscores.parquet")
        self.assertEqual(result["status"],"INDEPENDENT_SEASON_REPLICATION_UNAVAILABLE")
        self.assertFalse(result["validated_for_live_use"])
        self.assertEqual(result["promotion_gate"],"DO_NOT_ENABLE_LIVE_MODEL")

    def test_2024_defensive_matchups_reject_2025_season(self):
        box=pa.Table.from_pylist([
          {"player_id":10,"game_id":"0022400001","game_date":"2024-11-01",
           "team":"BOS","opponent":"NYK","minutes":30,"pts":20,
           "fgm":7,"fga":15,"fg3m":2,"fg3a":6,"ftm":4,"fta":5},
          {"player_id":11,"game_id":"0022400001","game_date":"2024-11-01",
           "team":"NYK","opponent":"BOS","minutes":30,"pts":20,
           "fgm":7,"fga":15,"fg3m":2,"fg3a":6,"ftm":4,"fta":5}])
        games=load_player_games(box,season_start=2024)
        template={"game_id":"0022400001","person_id":11,
            "matchups_person_id":10,"team_tricode":"NYK",
            "matchup_minutes":"10:00","partial_possessions":15,
            "matchup_field_goals_attempted":5,"matchup_field_goals_made":2,
            "matchup_three_pointers_attempted":2,
            "matchup_three_pointers_made":1,"_season":2025,"_season_type":"rg"}
        bad,_=load_defender_games(pa.Table.from_pylist([template]),games,season_start=2024)
        self.assertEqual(bad,[])
        good,_=load_defender_games(pa.Table.from_pylist([{**template,"_season":2024}]),
                                  games,season_start=2024)
        self.assertEqual(len(good),1)


if __name__=="__main__":unittest.main()

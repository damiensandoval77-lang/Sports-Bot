import unittest
from iphone_bot.defender_v3_holdout import evaluate,rows_from_parquet


class DefenderHoldoutTests(unittest.TestCase):
    def test_game_split_does_not_score_training_rows(self):
        rows=[]
        for number in range(125):
            gid="002250"+str(number).zfill(4)
            rows.append({"game_id":gid,"off_id":"1","def_id":"2",
                "poss":35.,"fga":12.,"fgm":5.,"minutes":18.})
        result=evaluate(rows)
        self.assertEqual(result["status"],"HISTORICAL_DEFENDER_EFFICIENCY_HOLDOUT")
        self.assertEqual(result["training_games"],100)
        self.assertEqual(result["test_games"],25)
        self.assertEqual(result["eligible_test_matchups"],25)
        self.assertEqual(result["eligible_test_fga"],300.)
        self.assertIsInstance(result["defender_brier_minus_baseline"],float)
        self.assertFalse(result["applied_to_live_ai"])

    def test_no_invented_improvement_when_small_sample(self):
        rows=[]
        for n in range(120):
            rows.append({"game_id":"002250"+str(n).zfill(4),
                "off_id":str(n),"def_id":"21","poss":1.,"fga":1.,"fgm":0.,"minutes":1.})
        result=evaluate(rows)
        self.assertEqual(result["eligible_test_matchups"],0)
        self.assertIsNone(result["defender_better_on_holdout"])

    def test_real_archived_schema_requires_verified_nba_games(self):
        import pyarrow as pa
        rows=[]
        for game,season in (("0022500001",2025),("0012500001",2025),("0022600001",2026)):
            rows.append({"game_id":game,"person_id":21,"matchups_person_id":10,
                "partial_possessions":20.,"matchup_minutes":"12:00",
                "matchup_field_goals_attempted":5,
                "matchup_field_goals_made":2,"_season":season,"_season_type":"rg"})
        converted=rows_from_parquet(pa.Table.from_pylist(rows))
        self.assertEqual(len(converted),1)
        self.assertEqual(converted[0]["game_id"],"0022500001")
        self.assertEqual(converted[0]["off_id"],"10")
        self.assertEqual(converted[0]["def_id"],"21")


if __name__=="__main__":unittest.main()

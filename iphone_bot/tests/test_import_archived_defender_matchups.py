import io
import unittest
from iphone_bot.import_archived_defender_matchups import normalize_schema,convert_table,import_data


def columns():
    return ["OFF_PLAYER_ID","DEF_PLAYER_ID","PARTIAL_POSS",
            "MATCHUP_MIN","MATCHUP_FGA","MATCHUP_FGM","_season","_season_type"]


class ImportArchiveTests(unittest.TestCase):
    def test_exact_schema_and_alternates(self):
        m=normalize_schema(columns())
        self.assertEqual(m["DEF_PLAYER_ID"],"DEF_PLAYER_ID")
        alt=["offPlayerId","defPlayerId","matchupPossessions",
             "matchupMinutes","matchupFGA","matchupFGM"]
        self.assertEqual(normalize_schema(alt)["OFF_PLAYER_ID"],"offPlayerId")

    def test_missing_and_ambiguous_columns_fail_closed(self):
        with self.assertRaises(ValueError):normalize_schema(columns()[:-3])
        with self.assertRaises(ValueError):normalize_schema(columns()+["offPlayerId"])

    def test_parquet_roundtrip_and_duplicate_aggregation(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        sample=[]
        for player in range(100,220):
            sample.append({"OFF_PLAYER_ID":player,"DEF_PLAYER_ID":21,
                "PARTIAL_POSS":80.,"MATCHUP_MIN":22.,
                "MATCHUP_FGA":22.,"MATCHUP_FGM":10.,
                "_season":2025,"_season_type":"rg"})
            sample.append({"OFF_PLAYER_ID":player,"DEF_PLAYER_ID":21,
                "PARTIAL_POSS":20.,"MATCHUP_MIN":6.,
                "MATCHUP_FGA":8.,"MATCHUP_FGM":4.,
                "_season":2025,"_season_type":"rg"})
        table=pa.Table.from_pylist(sample)
        buffer=io.BytesIO()
        pq.write_table(table,buffer)
        rows,headers,count=import_data(buffer.getvalue())
        self.assertEqual(count,240)
        self.assertEqual(len(rows),120)
        self.assertEqual(rows[0]["PARTIAL_POSS"],100.0)
        self.assertEqual(rows[0]["MATCHUP_FGM"],14.0)

    def test_real_archived_nba_v3_column_names_and_minutes(self):
        import pyarrow as pa
        sample=[]
        for i in range(100,220):
            sample.append({"person_id":21,"matchups_person_id":i,
                "partial_possessions":80.0,"matchup_minutes":"21:30",
                "matchup_field_goals_attempted":22,
                "matchup_field_goals_made":10,
                "_season":2025,"_season_type":"rg"})
        result=convert_table(pa.Table.from_pylist(sample))
        self.assertEqual(len(result),120)
        self.assertEqual(result[0]["DEF_PLAYER_ID"],"21")
        self.assertEqual(result[0]["OFF_PLAYER_ID"],"100")
        self.assertEqual(result[0]["MATCHUP_MIN"],21.5)

    def test_reject_playoff_or_leaking_season(self):
        import pyarrow as pa
        for season,kind in ((2026,"rg"),(2025,"po")):
            table=pa.Table.from_pylist([{"OFF_PLAYER_ID":100,"DEF_PLAYER_ID":101,
                "PARTIAL_POSS":80.,"MATCHUP_MIN":22.,"MATCHUP_FGA":20.,
                "MATCHUP_FGM":9.,"_season":season,"_season_type":kind}])
            with self.assertRaises(ValueError):convert_table(table)


if __name__=="__main__":unittest.main()

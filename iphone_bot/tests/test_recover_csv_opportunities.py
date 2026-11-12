"""Current-season public CSV fallback must use real complete opportunity fields."""
import unittest
from iphone_bot.recover_csv_opportunities import recover

ROW={"player":"Stephon Castle","id":"1642264","team":"SAS",
     "opponent":"CHI","date":"2026-11-08","PTS":20,"REB":5,"AST":4,
     "MIN":30,"FGM":8,"FGA":15,"FG3M":2,"FG3A":5,"FTM":2,
     "FTA":4,"OREB":1,"DREB":4,"TOV":2}

class CsvRecovery(unittest.TestCase):
    def test_complete_arithmetically_verified_public_box_can_fill_missing_parquet(self):
        got,report=recover([ROW],[],[])
        self.assertEqual(report["recovered"],1)
        self.assertEqual(got[0]["history_source_confidence"],
                         "SINGLE_SOURCE_PUBLIC_CSV_ARITHMETIC_VALIDATED")
        self.assertEqual(got[0]["FTA"],4)
        self.assertEqual(got[0]["OREB"],1)
        self.assertTrue(report["not_independently_crosschecked"])

    def test_never_replace_conflicting_independently_observed_box(self):
        parquet=[{"player_id":"1642264","team":"SAS","game_date":"2026-11-08"}]
        got,report=recover([ROW],[],parquet)
        self.assertEqual(got,[])
        self.assertEqual(report["recovered"],0)

    def test_no_duplicate_when_existing_crosscheck_present(self):
        got,report=recover([ROW],[{**ROW,"source":"TWO_SOURCES"}],[])
        self.assertEqual(report["recovered"],0)
        self.assertEqual(len(got),1)

    def test_missing_free_throw_attempts_are_not_replaced_with_zero(self):
        got,report=recover([{**ROW,"FTA":None}],[],[])
        self.assertEqual(got,[])
        self.assertEqual(report["recovered"],0)

    def test_false_scoring_or_rebound_arithmetic_is_rejected(self):
        for item in ({**ROW,"PTS":22},{**ROW,"REB":6},{**ROW,"FGM":12},
                     {**ROW,"FTM":7}):
            got,report=recover([item],[],[])
            self.assertEqual(got,[],item)
            self.assertEqual(report["recovered"],0)

    def test_conflicting_duplicate_csv_same_player_day_rejected(self):
        other={**ROW,"FGA":16}
        got,report=recover([ROW,other],[],[])
        self.assertEqual(got,[])
        self.assertEqual(report["conflicting_rows_rejected"],1)

    def test_2027_season_continuation_supported(self):
        got,report=recover([{**ROW,"date":"2027-01-10"}],[],[])
        self.assertEqual(report["recovered"],1)

if __name__=="__main__":
    unittest.main()

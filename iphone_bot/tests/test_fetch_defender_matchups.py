import unittest
from iphone_bot.fetch_defender_matchups import fetch,normalize_response


def payload():
    cols=["OFF_PLAYER_ID","DEF_PLAYER_ID","PARTIAL_POSS","MATCHUP_MIN",
          "MATCHUP_FGA","MATCHUP_FGM","GP"]
    return {"resultSets":[{"name":"SeasonMatchups","headers":cols,
                            "rowSet":[[10,21,100,30,40,14,4],
                                      [10,22,50,15,20,11,2],
                                      [10,23,0,0,0,0,0]]}]}


class DefenderSourceTests(unittest.TestCase):
    def test_exact_nba_matchup_schema(self):
        rows=normalize_response(payload())
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["OFF_PLAYER_ID"],10)
        self.assertEqual(rows[0]["MATCHUP_FGA"],40)

    def test_missing_columns_rejected(self):
        data=payload()
        data["resultSets"][0]["headers"][2]="NOT_REAL"
        with self.assertRaises(ValueError):normalize_response(data)

    def test_wrong_dataset_rejected(self):
        data=payload()
        data["resultSets"][0]["name"]="AnotherTable"
        with self.assertRaises(ValueError):normalize_response(data)

    def test_mock_provider_pipeline(self):
        rows=fetch(requester=payload)
        self.assertEqual(rows[1]["DEF_PLAYER_ID"],22)


if __name__=="__main__":unittest.main()

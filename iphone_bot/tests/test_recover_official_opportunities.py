"""No invented opportunity box stats, no lookahead, and exact NBA CDN identity."""
import unittest
from iphone_bot.recover_official_opportunities import recover,completed_row

LOCAL={"player":"Stephon Castle","id":"1642264","team":"SAS",
       "opponent":"CHI","date":"2026-11-08","PTS":20,"REB":5,"AST":6,
       "MIN":31}
GAME_ID="0022600123"
BOX={"game":{"gameId":GAME_ID,"gameStatus":3,
     "gameTimeUTC":"2026-11-09T01:00:00Z",
     "awayTeam":{"teamTricode":"SAS","players":[
         {"personId":1642264,"played":True,"statistics":{
             "points":20,"reboundsTotal":5,"assists":6,
             "minutes":"PT31M","fieldGoalsAttempted":15,
             "freeThrowsAttempted":4,"turnovers":2,"reboundsOffensive":1}}]},
     "homeTeam":{"teamTricode":"CHI","players":[]}}}
SCHEDULE={"leagueSchedule":{"seasonYear":"2026-27","gameDates":[
    {"gameDate":"2026-11-08","games":[
      {"gameId":GAME_ID,"awayTeam":{"teamTricode":"SAS"},
       "homeTeam":{"teamTricode":"CHI"}}]}]}}
FEED={"picks":[{"player":"Stephon Castle","team":"SAS",
                "pickem_tier":"standard","start":"2026-11-12T01:00:00Z"}]}

class OfficialOpportunityRecovery(unittest.TestCase):
    def test_exact_previously_completed_game_recovers_all_real_opportunity_fields(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            return BOX if "boxscore_" in url else SCHEDULE
        rows,report=recover([LOCAL],[],FEED,fetch=fetch)
        self.assertEqual(report["recovered"],1)
        self.assertEqual(report["requested_games"],1)
        self.assertEqual(rows[0]["id"],"1642264")
        self.assertEqual(rows[0]["FTA"],4)
        self.assertEqual(rows[0]["OREB"],1)
        self.assertEqual(rows[0]["FGA"],15)
        self.assertEqual(rows[0]["TOV"],2)
        self.assertEqual(rows[0]["verified_source"],"NBA_CDN_FINAL_OPPORTUNITY_HISTORY")
        self.assertEqual(len(calls),2)
        again,report2=recover([LOCAL],rows,FEED,fetch=fetch)
        self.assertEqual(report2["recovered"],0)
        self.assertEqual(len(again),1)

    def test_final_box_without_matching_player_id_never_creates_history(self):
        box={"game":{**BOX["game"],"awayTeam":{
            "teamTricode":"SAS","players":[{
                **BOX["game"]["awayTeam"]["players"][0],"personId":999999}]}}}
        self.assertIsNone(completed_row(LOCAL,GAME_ID,box,"2026-11-12"))

    def test_unfinished_game_and_wrong_official_points_fail(self):
        self.assertIsNone(completed_row(LOCAL,GAME_ID,{"game":{**BOX["game"],"gameStatus":2}},"2026-11-12"))
        bad={"game":{**BOX["game"],"awayTeam":{"teamTricode":"SAS","players":[{
            **BOX["game"]["awayTeam"]["players"][0],"statistics":{
                **BOX["game"]["awayTeam"]["players"][0]["statistics"],"points":21}}]}}}
        self.assertIsNone(completed_row(LOCAL,GAME_ID,bad,"2026-11-12"))

    def test_same_day_or_posttip_games_never_enter_forecast_history(self):
        self.assertIsNone(completed_row(LOCAL,GAME_ID,BOX,"2026-11-08"))
        today={**LOCAL,"date":"2026-11-12"}
        result,report=recover([today],[],FEED,fetch=lambda url: SCHEDULE)
        self.assertEqual(result,[])
        self.assertEqual(report["recovered"],0)

    def test_missing_opportunity_fields_are_not_silently_zero_filled(self):
        incomplete={"game":{**BOX["game"],"awayTeam":{"teamTricode":"SAS","players":[{
            **BOX["game"]["awayTeam"]["players"][0],
            "statistics":{k:v for k,v in BOX["game"]["awayTeam"]["players"][0]["statistics"].items()
                          if k!="freeThrowsAttempted"}}]}}}
        self.assertIsNone(completed_row(LOCAL,GAME_ID,incomplete,"2026-11-12"))

if __name__=="__main__":
    unittest.main()

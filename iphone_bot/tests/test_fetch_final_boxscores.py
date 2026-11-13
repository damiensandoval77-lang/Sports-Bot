"""Final-boxscore eligibility and verified completion regression tests."""
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from iphone_bot.fetch_final_boxscores import (
    pending_games,box_player,nba_boxscore_rows,espn_final_events,minutes,gather,verified_schedule_ids,final_schedule_boxscore,NBA_BOX,NBA_BOX_ALT,request_json
)

def pick(start="2026-11-06T00:00:00Z",status="PENDING"):
    return {"event_start":start,"game":"Boston Celtics @ Charlotte Hornets",
            "status":status,"player_id":"10","team":"BOS"}


class FinalBoxscoreSettlementTests(unittest.TestCase):
    def test_official_string_zero_inactive_with_iso_zero_minutes(self):
        game={"gameId":"0022600230","gameStatus":3,
              "gameTimeUTC":"2026-11-13T02:00:00Z",
              "awayTeam":{"teamTricode":"CHA"},"homeTeam":{"teamTricode":"PHX"}}
        player={"name":"Verified Inactive","played":"0","status":"INACTIVE",
                "notPlayingReason":"INACTIVE_INJURY",
                "statistics":{"points":0,"reboundsTotal":0,"assists":0,
                              "minutes":"PT00M00.00S"}}
        box={"game":{**game,"awayTeam":{"teamTricode":"CHA","players":[player]}}}
        for flag in (False,0,"0"):
            player["played"]=flag
            rows=nba_boxscore_rows(game,box)
            self.assertEqual(len(rows),1)
            self.assertTrue(rows[0]["dnp_final_verified"])
            self.assertNotIn("PTS",rows[0])
        for flag in (None,"",True,1,"1"):
            player["played"]=flag
            self.assertEqual(nba_boxscore_rows(game,box),[])
        player["played"]="0"
        for field,value in (("minutes","PT00M01.00S"),("fieldGoalsAttempted",1),("points",2)):
            with self.subTest(field=field):
                old=player["statistics"].get(field)
                player["statistics"][field]=value
                self.assertFalse(any(r.get("dnp_final_verified") for r in nba_boxscore_rows(game,box)))
                player["statistics"][field]=old

    def test_official_boxscore_origin_recovers_cdn_access_error(self):
        payload={"game":{"gameId":"0022600230","gameStatus":3}}
        with patch("iphone_bot.fetch_final_boxscores._request_json",side_effect=[OSError("403"),payload]) as fetch:
            self.assertEqual(request_json(NBA_BOX.format("0022600230")),payload)
            self.assertEqual(fetch.call_args_list[1].args[0],NBA_BOX_ALT.format("0022600230"))
        with patch("iphone_bot.fetch_final_boxscores._request_json",side_effect=OSError("unavailable")):
            with self.assertRaises(OSError):request_json(NBA_BOX.format("0022600230"))

    def test_actual_pending_game_enters_grading_window(self):
        now=datetime(2026,11,7,6,tzinfo=timezone.utc)
        games=pending_games([pick()],now)
        self.assertEqual(games,{("2026-11-05","BOS","CHA")})
        self.assertEqual(pending_games([pick(status="SETTLED")],now),set())

    def test_old_ungraded_night_remains_eligible_for_recovery(self):
        now=datetime(2026,11,20,6,tzinfo=timezone.utc)
        self.assertEqual(pending_games([pick()],now),
                         {("2026-11-05","BOS","CHA")})

    def test_not_yet_finished_games_are_not_eligible(self):
        now=datetime(2026,11,7,2,tzinfo=timezone.utc)
        self.assertEqual(pending_games([pick("2026-11-07T01:30:00Z")],now),set())

    def test_espn_requires_completed_event_status(self):
        fixture={"events":[{"id":"1","date":"2026-11-07T00:00:00Z",
                  "status":{"type":{"completed":False}},
                  "competitions":[{"competitors":[
                    {"homeAway":"away","team":{"abbreviation":"BOS"}},
                    {"homeAway":"home","team":{"abbreviation":"CHA"}}]}]}]}
        self.assertEqual(espn_final_events(fixture),[])
        fixture["events"][0]["status"]["type"]["completed"]=True
        self.assertEqual(len(espn_final_events(fixture)),1)

    def test_minutes_and_exact_final_player_boxscore(self):
        self.assertAlmostEqual(minutes("PT32M30S"),32.5)
        valid=box_player("Real Player","BOS","CHA","2026-11-06",
            24,8,7,"30:00","ESPN_FINAL","123")
        self.assertTrue(valid["final_confirmed"])
        self.assertEqual(valid["PRA"],39)
        self.assertIsNone(box_player("Real Player","BOS","BOS",
            "2026-11-06",24,8,7,30,"ESPN_FINAL","123"))
        self.assertIsNone(box_player("Real Player","BOS","CHA",
            "2026-11-06",24,8,7,None,"ESPN_FINAL","123"))

    def test_confirmed_final_inactive_player_is_explicit_dnp(self):
        game={"gameId":"0022600099","gameStatus":3,
              "gameTimeUTC":"2026-11-08T01:40:00Z",
              "awayTeam":{"teamTricode":"ORL"},
              "homeTeam":{"teamTricode":"GSW"}}
        box={"game":dict(game)}
        box["game"]["awayTeam"]={"teamTricode":"ORL","players":[
            {"name":"Desmond Bane","played":False,"notPlayingReason":"INACTIVE",
             "status":"INACTIVE","statistics":{}}]}
        box["game"]["homeTeam"]={"teamTricode":"GSW","players":[]}
        rows=nba_boxscore_rows(game,box)
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]["dnp_final_verified"])
        self.assertEqual(rows[0]["player"],"Desmond Bane")
        box["game"]["gameStatus"]=2
        with self.assertRaises(ValueError):nba_boxscore_rows(game,box)

    def test_inactive_with_null_stats_recovers_but_missing_player_does_not(self):
        game={"gameId":"0022600099","gameStatus":3,
              "gameTimeUTC":"2026-11-08T01:40:00Z",
              "awayTeam":{"teamTricode":"ORL"},
              "homeTeam":{"teamTricode":"GSW"}}
        box={"game":dict(game)}
        box["game"]["awayTeam"]={"teamTricode":"ORL","players":[
            {"name":"Verified Inactive","played":False,"status":"INACTIVE",
             "statistics":None},
            {"name":"No Evidence","played":False,"statistics":None},
            {"name":"Contradictory","played":False,"status":"INACTIVE",
             "statistics":{"points":15}}]}
        box["game"]["homeTeam"]={"teamTricode":"GSW","players":[]}
        rows=nba_boxscore_rows(game,box)
        self.assertEqual([x["player"] for x in rows],["Verified Inactive"])
        self.assertEqual(rows[0]["dnp_reason"],"INACTIVE")
        self.assertTrue(rows[0]["dnp_final_verified"])

    def test_verified_official_schedule_finds_exact_2026_nba_matchup(self):
        wanted={("2026-11-06","BOS","CHA")}
        payload={"leagueSchedule":{"seasonYear":"2026-27","gameDates":[
            {"gameDate":"2026-11-06","games":[
              {"gameId":"0022600011","awayTeam":{"teamTricode":"BOS"},
               "homeTeam":{"teamTricode":"CHA"}},
              {"gameId":"0022600012","awayTeam":{"teamTricode":"NYK"},
               "homeTeam":{"teamTricode":"CHA"}}]}]}}
        self.assertEqual(verified_schedule_ids(payload,wanted),
                         {("2026-11-06","BOS","CHA"):"0022600011"})
        payload["leagueSchedule"]["seasonYear"]="2025-26"
        with self.assertRaises(ValueError):verified_schedule_ids(payload,wanted)

    def test_schedule_is_not_a_final_result_without_final_boxscore(self):
        key=("2026-11-06","BOS","CHA")
        def request(url):
            self.assertEqual(url,NBA_BOX.format("0022600011"))
            return {"game":{"gameId":"0022600011","gameStatus":2,
                    "gameTimeUTC":"2026-11-07T00:00:00Z",
                    "awayTeam":{"teamTricode":"BOS"},
                    "homeTeam":{"teamTricode":"CHA"}}}
        self.assertEqual(final_schedule_boxscore("0022600011",key,request),[])

    def test_no_pending_matches_never_calls_provider(self):
        def blocked(_):
            raise AssertionError("Provider should not be queried for empty pending matchups")
        found,status=gather([],request=blocked)
        self.assertEqual(found,[])
        self.assertEqual(status["status"],"NO_ELIGIBLE_PENDING_MATCHUPS")

if __name__=="__main__":unittest.main()

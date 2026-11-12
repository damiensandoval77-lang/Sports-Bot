import unittest
from iphone_bot.fetch_final_boxscores import (
    nba_boxscore_rows,espn_boxscore_rows,espn_final_events,pending_games,
    gather,minutes,NBA_SCOREBOARD,NBA_BOX,NBA_SCHEDULE,NBA_SCHEDULE_ALT,ESPN_SCORE,ESPN_BOX)
from iphone_bot.paper_pick_pipeline import snapshot,settle,summary


def nba_fixture(final=True):
    game={"gameId":"0022600123","gameStatus":3 if final else 2,
          "gameTimeUTC":"2026-11-13T03:00:00Z",
          "awayTeam":{"teamTricode":"BOS"},
          "homeTeam":{"teamTricode":"MIA"}}
    return game,{"game":{**game,
        "awayTeam":{"teamTricode":"BOS","players":[{
            "name":"Sample Player","statistics":{
                "points":26,"reboundsTotal":5,"assists":4,
                "minutes":"PT30M12S"}}]},
        "homeTeam":{"teamTricode":"MIA","players":[]}}}


def market():
    return {"player":"Sample Player","player_id":"123","team":"BOS",
      "game":"Boston Celtics @ Miami Heat","start":"2026-11-13T03:00:00Z",
      "stat":"PTS","projection":24.2,"shadow_projection":26.4,
      "combined_projection":25.3,"combined_model_count":2,
      "book_quotes":[{"name":"FanDuel","line":22.5,
       "over":-110,"under":-110,"over_model_probability":.72}]}


class FinalBoxscoreTests(unittest.TestCase):
    def test_final_nba_boxscore_grade_early_with_name_team_and_date(self):
        event,box=nba_fixture()
        direct=nba_boxscore_rows(event,box)
        self.assertEqual(len(direct),1)
        self.assertAlmostEqual(direct[0]["MIN"],30.2)
        locked=snapshot([market()],"2026-11-13T00:00:00Z")
        # Start 10pm ET, final boxscore is valid by 1:05am ET, earlier than CSV.
        graded=settle(locked,direct,"2026-11-13T06:05:00Z")
        self.assertEqual(graded[0]["status"],"SETTLED")
        self.assertEqual(graded[0]["actual"],26)
        self.assertEqual(graded[0]["settlement_source"],"NBA_CDN_FINAL")
        self.assertEqual(summary(graded)["performance"]["models"]["combined"]["direction_wins"],1)

    def test_not_final_and_before_three_hours_remain_pending(self):
        event,box=nba_fixture(final=False)
        with self.assertRaises(ValueError):nba_boxscore_rows(event,box)
        event,box=nba_fixture()
        locked=snapshot([market()],"2026-11-13T00:00:00Z")
        direct=nba_boxscore_rows(event,box)
        self.assertEqual(settle(locked,direct,"2026-11-13T04:59:00Z")[0]["status"],"PENDING")

    def test_wrong_player_team_date_or_ambiguous_match_does_not_grade(self):
        event,box=nba_fixture()
        row=nba_boxscore_rows(event,box)[0]
        # 03:00 UTC on Nov 13 is 10:00 PM EST on Nov 12.
        self.assertEqual(row["date"],"2026-11-12")
        locked=snapshot([market()],"2026-11-13T00:00:00Z")
        for changed in ({"player":"Similar Player"},{"team":"MIA"},
                        {"date":"2026-11-11"},{"opponent":"NYK"}):
            self.assertEqual(settle(locked,[{**row,**changed}],
                "2026-11-13T07:00:00Z")[0]["status"],"PENDING")
        self.assertEqual(settle(locked,[row,row],
            "2026-11-13T07:00:00Z")[0]["status"],"SETTLED")
        self.assertEqual(settle(locked,[row,{**row,"AST":5}],
            "2026-11-13T07:00:00Z")[0]["status"],"PENDING")

    def test_minutes_and_invalid_players_excluded(self):
        self.assertEqual(minutes("PT23M30S"),23.5)
        self.assertAlmostEqual(minutes("30:45"),30.75)
        event,box=nba_fixture()
        box["game"]["awayTeam"]["players"][0]["statistics"]["minutes"]="PT0M"
        self.assertEqual(nba_boxscore_rows(event,box),[])

    def test_espn_completed_summary_and_name_matching(self):
        event={"id":"4000123","date":"2026-11-13T03:00:00Z",
         "status":{"type":{"completed":True}},
         "competitions":[{"competitors":[
             {"homeAway":"away","team":{"abbreviation":"BOS"}},
             {"homeAway":"home","team":{"abbreviation":"MIA"}}]}]}
        summary_data={"header":{"id":"4000123","competitions":[{}]},
         "boxscore":{"players":[{"team":{"abbreviation":"BOS"},
          "statistics":[{"names":["MIN","REB","AST","PTS"],
           "athletes":[{"athlete":{"displayName":"Sample Player"},
                        "stats":["30:12","5","4","26"]}]}]}]}}
        self.assertEqual(len(espn_final_events({"events":[event]})),1)
        rows=espn_boxscore_rows(event,summary_data)
        self.assertEqual(rows[0]["source"],"ESPN_FINAL")
        locked=snapshot([market()],"2026-11-13T00:00:00Z")
        self.assertEqual(settle(locked,rows,"2026-11-13T07:00:00Z")[0]["status"],"SETTLED")
        not_done={**event,"status":{"type":{"completed":False}}}
        self.assertEqual(espn_final_events({"events":[not_done]}),[])

    def test_pending_full_team_name_maps_to_abbreviations_and_both_provider_paths(self):
        locked=snapshot([market()],"2026-11-13T00:00:00Z")
        now=__import__("datetime").datetime.fromisoformat("2026-11-13T06:20:00+00:00")
        self.assertEqual(pending_games(locked,now),{("2026-11-12","BOS","MIA")})
        event,box=nba_fixture()
        def request(url):
            if url==NBA_SCOREBOARD:return {"scoreboard":{"games":[event]}}
            if url==NBA_BOX.format(event["gameId"]):return box
            raise AssertionError("No ESPN fetch should happen when NBA game is complete")
        rows,report=gather(locked,now,request)
        self.assertEqual(report["final_nba_games"],1)
        self.assertEqual(len(rows),1)

    def test_nba_read_timeout_falls_back_to_espn_final(self):
        locked=snapshot([market()],"2026-11-13T00:00:00Z")
        now=__import__("datetime").datetime.fromisoformat("2026-11-13T06:20:00+00:00")
        event={"id":"4000123","date":"2026-11-13T03:00:00Z",
               "status":{"type":{"completed":True}},
               "competitions":[{"competitors":[
                  {"homeAway":"away","team":{"abbreviation":"BOS"}},
                  {"homeAway":"home","team":{"abbreviation":"MIA"}}]}]}
        stats={"header":{"id":"4000123","competitions":[{}]},
          "boxscore":{"players":[{"team":{"abbreviation":"BOS"},
            "statistics":[{"names":["MIN","REB","AST","PTS"],
              "athletes":[{"athlete":{"displayName":"Sample Player"},
                           "stats":["30:12","5","4","26"]}]}]}]}}
        def request(url):
            if url==NBA_SCOREBOARD:raise TimeoutError("The read operation timed out")
            if url in (NBA_SCHEDULE,NBA_SCHEDULE_ALT):raise TimeoutError("NBA schedule unavailable")
            if url.startswith(ESPN_SCORE):return {"events":[event]}
            if url.startswith(ESPN_BOX):return stats
            raise AssertionError(url)
        rows,report=gather(locked,now,request)
        self.assertEqual(report["final_espn_games"],1)
        self.assertEqual(report["final_nba_games"],0)
        self.assertEqual(rows[0]["source"],"ESPN_FINAL")
        self.assertTrue(any("timed out" in e for e in report["errors"]))
        graded=settle(locked,rows,now.isoformat())
        self.assertEqual(graded[0]["status"],"SETTLED")

    def test_all_providers_timeout_does_not_abort_grading(self):
        locked=snapshot([market()],"2026-11-13T00:00:00Z")
        now=__import__("datetime").datetime.fromisoformat("2026-11-13T06:20:00+00:00")
        def timeout(_):raise TimeoutError("read timed out")
        rows,report=gather(locked,now,timeout)
        self.assertEqual(rows,[])
        self.assertEqual(report["status"],"NO_FINAL_BOXSCORES_AVAILABLE")
        self.assertGreaterEqual(len(report["errors"]),2)
        self.assertEqual(settle(locked,rows,now.isoformat())[0]["status"],"PENDING")

    def test_no_pending_matchups_skips_provider_calls(self):
        def never_called(_):raise AssertionError("No network expected")
        now=__import__("datetime").datetime.fromisoformat("2026-11-13T06:20:00+00:00")
        rows,report=gather([],now,never_called)
        self.assertEqual(rows,[])
        self.assertEqual(report["status"],"NO_ELIGIBLE_PENDING_MATCHUPS")

    def test_source_failure_does_not_create_fake_grades(self):
        locked=snapshot([market()],"2026-11-13T00:00:00Z")
        now=__import__("datetime").datetime.fromisoformat("2026-11-13T06:20:00+00:00")
        def unavailable(_):raise __import__("urllib").error.URLError("blocked")
        rows,report=gather(locked,now,unavailable)
        self.assertEqual(rows,[])
        self.assertGreater(len(report["errors"]),0)


if __name__=="__main__":unittest.main()

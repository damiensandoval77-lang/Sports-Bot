import tempfile
import unittest
import json
from datetime import datetime,timezone
from pathlib import Path
from scripts.fetch_nfl_live import parse_scoreboard,parse_summary,snapshot

class NFLLiveTests(unittest.TestCase):
    def game(self):
        return {"game_id":"2026_09_BUF_MIN","season":2026,"week":9,"away":"BUF","home":"MIN",
                "kickoff_utc":"2026-11-10T01:15:00+00:00"}
    def scoreboard(self):
        return {"events":[{"id":"12345","date":"2026-11-10T01:15:00Z",
            "status":{"type":{"state":"in","shortDetail":"Q1 10:23"},"period":1,"displayClock":"10:23"},
            "competitions":[{"competitors":[
                {"homeAway":"home","team":{"abbreviation":"MIN"},"score":"3"},
                {"homeAway":"away","team":{"abbreviation":"BUF"},"score":"0"}]}]}]}
    def summary(self):
        return {"boxscore":{"players":[{"team":{"abbreviation":"MIN"},
             "statistics":[
              {"name":"rushing","labels":["CAR","YDS","AVG","TD"],
               "athletes":[{"athlete":{"id":"55","displayName":"Runner Example"},
                            "stats":["8","31","3.9","1"]}]},
              {"name":"receiving","labels":["REC","YDS","AVG","TD","LONG","TGTS"],
               "athletes":[{"athlete":{"id":"55","displayName":"Runner Example"},
                            "stats":["3","20","6.7","0","14","4"]}]}]}]}}
    def test_public_espn_score_and_player_stat_mapping(self):
        event=parse_scoreboard(self.scoreboard(),[self.game()])["2026_09_BUF_MIN"]
        self.assertEqual(event["status"],"in")
        self.assertEqual(event["home_score"],3)
        p=parse_summary(self.summary(),"BUF","MIN")[0]
        self.assertEqual(p["stats"]["RUSH_ATT"],8)
        self.assertEqual(p["stats"]["RUSH_YDS"],31)
        self.assertEqual(p["stats"]["TGT"],4)
        self.assertEqual(p["stats"]["RUSH_REC_YDS"],51)
    def test_missing_stats_not_zero(self):
        data=self.summary()
        data["boxscore"]["players"][0]["statistics"][1]["athletes"][0]["stats"]=["3","--","6.7","0","14","4"]
        p=parse_summary(data,"BUF","MIN")[0]
        self.assertNotIn("REC_YDS",p["stats"])
        self.assertNotIn("RUSH_REC_YDS",p["stats"])
    def test_wrong_game_and_wrong_date_not_attached(self):
        other={**self.game(),"game_id":"2026_11_BUF_MIN",
               "kickoff_utc":"2026-11-24T01:15:00Z"}
        self.assertNotIn(other["game_id"],parse_scoreboard(self.scoreboard(),[other]))
    def test_snapshot_reads_game_without_mutating_schedule(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            original={"season":2026,"games":[self.game()]}
            (path/"schedule_2026.json").write_text(json.dumps(original))
            def fetch(url):
                return self.summary() if "summary?" in url else self.scoreboard()
            result=snapshot(datetime(2026,11,10,1,20,tzinfo=timezone.utc),
                            fetch=fetch,data_dir=path)
            self.assertEqual(result["status"],"ok")
            self.assertEqual(result["games"][0]["players"][0]["stats"]["REC"],3)
            self.assertEqual(json.loads((path/"schedule_2026.json").read_text()),original)
    def test_monday_night_scoreboard_queries_eastern_and_utc_dates(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            (path/"schedule_2026.json").write_text(json.dumps({"games":[self.game()]}))
            queried=[]
            def fetch(url):
                if "scoreboard?" in url:
                    queried.append(url)
                    return self.scoreboard()
                return self.summary()
            snapshot(datetime(2026,11,10,1,20,tzinfo=timezone.utc),
                     fetch=fetch,data_dir=path)
            self.assertTrue(any("dates=20261109" in url for url in queried))
            self.assertTrue(any("dates=20261110" in url for url in queried))
    def test_empty_date_results_fallback_to_current_week_scoreboard(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            (path/"schedule_2026.json").write_text(json.dumps({"games":[self.game()]}))
            requested=[]
            def fetch(url):
                requested.append(url)
                if "summary?" in url:return self.summary()
                if "dates=" in url:return {"events":[]}
                return self.scoreboard()
            data=snapshot(datetime(2026,11,10,1,50,tzinfo=timezone.utc),
                          fetch=fetch,data_dir=path)
            self.assertEqual(data["games"][0]["game_id"],"2026_09_BUF_MIN")
            self.assertEqual(data["games"][0]["players"][0]["stats"]["RUSH_YDS"],31)
            self.assertTrue(any(x.endswith("/scoreboard") for x in requested))
    def test_empty_date_and_default_scoreboard_uses_matching_week_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            (path/"schedule_2026.json").write_text(json.dumps({"games":[self.game()]}))
            requested=[]
            def fetch(url):
                requested.append(url)
                if "summary?" in url:return self.summary()
                if "seasontype=2&week=9" in url:return self.scoreboard()
                return {"events":[]}
            data=snapshot(datetime(2026,11,10,1,50,tzinfo=timezone.utc),
                          fetch=fetch,data_dir=path)
            self.assertEqual(len(data["games"]),1)
            self.assertTrue(any("week=9" in x for x in requested))
    def test_unrelated_week_default_scoreboard_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            (path/"schedule_2026.json").write_text(json.dumps({"games":[self.game()]}))
            board=self.scoreboard()
            board["events"][0]["date"]="2026-11-24T01:15:00Z"
            data=snapshot(datetime(2026,11,10,1,50,tzinfo=timezone.utc),
                          fetch=lambda url:board,data_dir=path)
            self.assertEqual(data["games"],[])
            self.assertIn("no_matching_scheduled_game",str(data["errors"]))
    def test_feed_failures_have_explicit_status_not_fabricated_stats(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            (path/"schedule_2026.json").write_text(json.dumps({"games":[self.game()]}))
            result=snapshot(datetime(2026,11,10,1,20,tzinfo=timezone.utc),
                fetch=lambda url: (_ for _ in ()).throw(OSError("offline")),data_dir=path)
            self.assertEqual(result["status"],"partial_or_unavailable")
            self.assertEqual(result["games"],[])
            self.assertNotIn("players",result)
if __name__=="__main__":unittest.main()

class NFLTeamAliasTests(NFLLiveTests):
    def test_washington_alias_matches_scoreboard_and_player_totals(self):
        game={**self.game(),"away":"WAS"}
        board=self.scoreboard()
        board["events"][0]["competitions"][0]["competitors"][1]["team"]["abbreviation"]="WSH"
        result=parse_scoreboard(board,[game])[game["game_id"]]
        self.assertEqual(result["away"],"WAS")
        summary=self.summary()
        summary["boxscore"]["players"][0]["team"]["abbreviation"]="WSH"
        players=parse_summary(summary,"WAS","MIN")
        self.assertEqual(players[0]["team"],"WAS")
        self.assertEqual(players[0]["stats"]["RUSH_REC_YDS"],51)
        game["kickoff_utc"]="2026-11-24T01:15:00Z"
        self.assertEqual(parse_scoreboard(board,[game]),{})

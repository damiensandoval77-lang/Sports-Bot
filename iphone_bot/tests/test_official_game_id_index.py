import datetime as dt
import tempfile
import unittest
from pathlib import Path
from iphone_bot.official_game_id_index import (
    entries_from_scoreboard,merge_entries,matching_ids,read_index,update_index)
from iphone_bot.fetch_final_boxscores import (
    gather,NBA_SCOREBOARD,NBA_BOX,NBA_SCHEDULE,NBA_SCHEDULE_ALT,ESPN_SCORE)

DAY="2026-11-08"
GID="0022600198"
GAME={"id":GID,"date_eastern":DAY,"start":"2026-11-09T00:00:00Z",
      "away_abbreviation":"MIA","home_abbreviation":"SAC",
      "game":"Miami Heat @ Sacramento Kings"}
SCORE={"status":"OBSERVED_NBA_LIVE_SCOREBOARD",
       "source":"NBA official liveData scoreboard via mediaops S3",
       "games":[GAME]}
PENDING=[{"status":"PENDING","event_start":GAME["start"],
          "game":GAME["game"],"team":"MIA","player_id":"123"}]
NOW=dt.datetime(2026,11,9,18,tzinfo=dt.timezone.utc)

def final_box(status=3,away="MIA"):
    return {"game":{"gameId":GID,"gameStatus":status,
            "gameTimeUTC":GAME["start"],
            "awayTeam":{"teamTricode":away,"players":[{
                "name":"Example Player",
                "statistics":{"points":21,"reboundsTotal":7,
                              "assists":4,"minutes":"PT32M"}}]},
            "homeTeam":{"teamTricode":"SAC","players":[]}}}

class OfficialGameIdTests(unittest.TestCase):
    def test_only_actual_official_nba_scoreboard_yields_game_id(self):
        self.assertEqual(entries_from_scoreboard(SCORE),[
            {"date":DAY,"away":"MIA","home":"SAC","game_id":GID}])
        self.assertEqual(entries_from_scoreboard({**SCORE,"source":"ESPN scoreboard"}),[])
        self.assertEqual(entries_from_scoreboard({**SCORE,"status":"STALE_UPSTREAM_ERROR"}),[])
        self.assertEqual(entries_from_scoreboard({**SCORE,"games":[{**GAME,"id":"401909958"}]}),[])

    def test_index_survives_daily_rollover_and_is_exact(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"index.json"
            self.assertEqual(update_index(p,SCORE),1)
            self.assertEqual(update_index(p,{**SCORE,"games":[]}),1)
            self.assertEqual(len(read_index(p)),1)
            self.assertEqual(matching_ids(read_index(p),{(DAY,"MIA","SAC")}),
                             {(DAY,"MIA","SAC"):GID})
            self.assertEqual(matching_ids(read_index(p),{(DAY,"SAC","MIA")}),{})

    def test_conflicting_verified_ids_fail_closed(self):
        entries=entries_from_scoreboard(SCORE)
        clash={**entries[0],"game_id":"0022600199"}
        self.assertEqual(merge_entries(entries,[clash]),[])

    def test_recover_exact_verified_final_with_schedule_offline(self):
        def request(url):
            if url==NBA_SCOREBOARD:return {"scoreboard":{"games":[]}}
            if url==NBA_BOX.format(GID):return final_box()
            if url in (NBA_SCHEDULE,NBA_SCHEDULE_ALT) or url.startswith(ESPN_SCORE):
                raise AssertionError("No schedule or ESPN fetch needed")
            raise AssertionError(url)
        rows,report=gather(PENDING,now=NOW,request=request,
                            known_game_ids=entries_from_scoreboard(SCORE))
        self.assertEqual(report.get("final_cached_id_nba_games"),1)
        self.assertEqual(report["final_nba_games"],1)
        self.assertEqual(rows[0]["PTS"],21)
        self.assertEqual(rows[0]["source_game_id"],GID)

    def test_known_id_does_not_fabricate_a_final(self):
        calls=[]
        def request(url):
            calls.append(url)
            if url==NBA_SCOREBOARD:return {"scoreboard":{"games":[]}}
            if url==NBA_BOX.format(GID):return final_box(status=2)
            if url in (NBA_SCHEDULE,NBA_SCHEDULE_ALT):raise TimeoutError("No schedule")
            if url.startswith(ESPN_SCORE):raise TimeoutError("No ESPN")
            raise AssertionError(url)
        rows,report=gather(PENDING,now=NOW,request=request,
                            known_game_ids=entries_from_scoreboard(SCORE))
        self.assertEqual(rows,[])
        self.assertEqual(report["status"],"NO_FINAL_BOXSCORES_AVAILABLE")
        self.assertIn(NBA_BOX.format(GID),calls)

    def test_wrong_team_final_box_is_rejected(self):
        def request(url):
            if url==NBA_SCOREBOARD:return {"scoreboard":{"games":[]}}
            if url==NBA_BOX.format(GID):return final_box(away="BOS")
            if url in (NBA_SCHEDULE,NBA_SCHEDULE_ALT):raise TimeoutError("No schedule")
            if url.startswith(ESPN_SCORE):raise TimeoutError("No ESPN")
            raise AssertionError(url)
        rows,report=gather(PENDING,now=NOW,request=request,
                            known_game_ids=entries_from_scoreboard(SCORE))
        self.assertEqual(rows,[])
        self.assertTrue(any("Cached official ID" in msg for msg in report["errors"]))

if __name__=="__main__":unittest.main()

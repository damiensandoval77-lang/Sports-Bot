"""Third-party NBA schedule parses Eastern calendar and live/finished games."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from iphone_bot.fetch_nba_schedule import collect,parse_event,parse_nba_game,nba_season_schedule,odds_schedule_fallback,EASTERN


def event(id="1",start="2026-11-07T00:30:00Z",state="pre"):
    return {"id":id,"date":start,
            "competitions":[{"competitors":[
                {"homeAway":"away","team":{"displayName":"Boston Celtics","abbreviation":"BOS"}},
                {"homeAway":"home","team":{"displayName":"Charlotte Hornets","abbreviation":"CHA"}}]}],
            "status":{"type":{"state":state}}}


class ScheduleTests(unittest.TestCase):
    def test_eastern_date_and_complete_status(self):
        day=dt.date(2026,11,6)
        row=parse_event(event(state="in"),day)
        self.assertEqual(row["date_eastern"],"2026-11-06")
        self.assertEqual(row["game_state"],"in")
        self.assertEqual(row["game"],"Boston Celtics @ Charlotte Hornets")
        self.assertIsNone(parse_event(event(),day+dt.timedelta(days=1)))

    def test_completed_events_are_not_dropped(self):
        day=dt.date(2026,11,6)
        rows=collect([day],lambda _: [event("1",state="post"),
                                     event("2",state="in"),
                                     event("3",state="pre")])
        self.assertEqual(rows["total_games"],3)
        self.assertEqual({g["game_state"] for g in rows["games"]},{"post","in","pre"})
        self.assertFalse(rows["has_sportsbook_props"])
        self.assertFalse(rows["has_verified_player_availability"])

    def test_invalid_events_are_not_invented(self):
        day=dt.date(2026,11,6)
        result=collect([day],lambda _: [event(),{"id":"bad"}])
        self.assertEqual(result["total_games"],1)
        self.assertEqual(result["source_records_rejected"],1)

    def test_nba_cdn_games_use_correct_eastern_date_and_status(self):
        day=dt.date(2026,11,6)
        game={"gameId":"0022600042","gameDateTimeUTC":"2026-11-07T00:30:00Z",
              "gameStatus":2,
              "awayTeam":{"teamCity":"Boston","teamName":"Celtics","teamTricode":"BOS"},
              "homeTeam":{"teamCity":"Charlotte","teamName":"Hornets","teamTricode":"CHA"}}
        row=parse_nba_game(game,{day})
        self.assertEqual(row["game"],"Boston Celtics @ Charlotte Hornets")
        self.assertEqual(row["game_state"],"in")
        self.assertIsNone(parse_nba_game(game,{dt.date(2026,11,7)}))

    def test_espn_scores_only_for_live_and_final_games(self):
        day=dt.date(2026,11,6)
        live=event(state="in")
        live["competitions"][0]["competitors"][0]["score"]="108"
        live["competitions"][0]["competitors"][1]["score"]="112"
        live["status"]["period"]=4
        live["status"]["displayClock"]="2:33"
        row=parse_event(live,day)
        self.assertEqual((row["away_score"],row["home_score"]),(108,112))
        self.assertEqual((row["period"],row["clock"]),(4,"2:33"))
        pre=event(state="pre")
        pre["competitions"][0]["competitors"][0]["score"]="0"
        pre["competitions"][0]["competitors"][1]["score"]="0"
        row=parse_event(pre,day)
        self.assertIsNone(row["away_score"])
        self.assertIsNone(row["home_score"])
        invalid=event(state="post")
        invalid["competitions"][0]["competitors"][0]["score"]="not-a-score"
        invalid["competitions"][0]["competitors"][1]["score"]="100"
        row=parse_event(invalid,day)
        self.assertIsNone(row["away_score"])
        self.assertEqual(row["home_score"],100)

    def test_nba_cdn_final_scores_preserved(self):
        game={"gameId":"0022600042","gameDateTimeUTC":"2026-11-07T00:30:00Z",
              "gameStatus":3,
              "awayTeam":{"teamCity":"Boston","teamName":"Celtics",
                          "teamTricode":"BOS","score":120},
              "homeTeam":{"teamCity":"Charlotte","teamName":"Hornets",
                          "teamTricode":"CHA","score":116}}
        result=parse_nba_game(game,{dt.date(2026,11,6)})
        self.assertEqual(result["game_state"],"post")
        self.assertEqual(result["away_score"],120)
        self.assertEqual(result["home_score"],116)

    def test_nba_cdn_first_endpoint_failure_falls_back_to_second(self):
        day=dt.date(2026,11,6)
        game={"gameId":"001","gameDateTimeUTC":"2026-11-07T00:30:00Z",
              "gameStatus":1,
              "awayTeam":{"teamCity":"Boston","teamName":"Celtics","teamTricode":"BOS"},
              "homeTeam":{"teamCity":"Charlotte","teamName":"Hornets","teamTricode":"CHA"}}
        urls=[]
        def reader(url):
            urls.append(url)
            if len(urls)==1:raise ValueError("bad first endpoint")
            return {"leagueSchedule":{"seasonYear":"2026-27",
                    "gameDates":[{"games":[game]}]*30}}
        result=nba_season_schedule([day],reader)
        self.assertEqual(len(urls),2)
        self.assertEqual(len(result["events"]),1)
        self.assertEqual(result["events"][0]["away_abbreviation"],"BOS")

    def test_cached_odds_fallback_is_partial_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"odds.json"
            record={"game":"Boston Celtics @ Charlotte Hornets",
                    "start":"2026-11-07T00:30:00Z"}
            path.write_text(json.dumps({"picks":[record,record]}))
            result=odds_schedule_fallback([dt.date(2026,11,6)],path)
            self.assertEqual(len(result["events"]),1)
            self.assertIn("partial",result["source"])
            self.assertEqual(result["events"][0]["game_state"],"unknown")
            self.assertIsNone(result["events"][0]["home_abbreviation"])

    def test_cached_odds_does_not_claim_empty_full_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"odds.json"
            path.write_text(json.dumps({"picks":[]}))
            with self.assertRaises(ValueError):
                odds_schedule_fallback([dt.date(2026,11,6)],path)

    def test_next_day_is_separate(self):
        today=dt.date(2026,11,6)
        tomorrow=today+dt.timedelta(days=1)
        a=event("A",start="2026-11-07T00:30:00Z")
        b=event("B",start="2026-11-08T00:30:00Z")
        result=collect([today,tomorrow],lambda _: [a,b])
        self.assertEqual(result["total_games"],2)
        self.assertEqual({g["date_eastern"] for g in result["games"]},
                         {"2026-11-06","2026-11-07"})


if __name__=="__main__":unittest.main()

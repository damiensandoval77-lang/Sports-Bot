import datetime as dt
import unittest

from iphone_bot.refresh_nba_player_boxscores import collect_boxscores, waiting_for_tipoff, NBA_LIVE_URLS, BOX_BASES, publishable_observations, verified_started

DAY=dt.date(2026,11,9)
NOW=dt.datetime(2026,11,9,23,30,tzinfo=dt.timezone.utc)

def game(status=2):
    return {"gameId":"0022600200","gameTimeUTC":"2026-11-09T23:00:00Z",
            "gameStatus":status,"period":2,"gameStatusText":"Q2",
            "homeTeam":{"teamTricode":"BOS","teamName":"Celtics","teamCity":"Boston","score":45},
            "awayTeam":{"teamTricode":"NYK","teamName":"Knicks","teamCity":"New York","score":42}}

def box():
    return {"game":{"gameId":"0022600200",
            "homeTeam":{"teamTricode":"BOS","players":[{"personId":11,"name":"Home Player",
                  "statistics":{"points":12,"reboundsTotal":4,"assists":5}}]},
            "awayTeam":{"teamTricode":"NYK","players":[{"personId":22,"name":"Away Player",
                  "statistics":{"points":20,"reboundsTotal":3,"assists":2}}]}}}

class LiveBoxscoreTests(unittest.TestCase):
    def test_live_player_totals_not_guesses(self):
        def fetch(url):
            return {"scoreboard":{"games":[game()]}} if url in NBA_LIVE_URLS else box()
        result=collect_boxscores(DAY,fetch=fetch,now=NOW)
        self.assertEqual(result["status"],"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES")
        self.assertEqual(next(p["PRA"] for p in result["games"][0]["player_rows"] if p["player"]=="Home Player"),21)
        self.assertEqual(result["coverage"]["observed_game_count"],1)
        self.assertTrue(result["not_sportsbook_lines"])

    def test_pregame_has_no_player_rows(self):
        result=collect_boxscores(DAY,fetch=lambda _:{"scoreboard":{"games":[game(1)]}},now=NOW)
        self.assertEqual(result["games"],[])
        self.assertEqual(result["coverage"]["active_or_final_count"],0)

    def test_wrong_day_is_not_live(self):
        prior=game()
        prior["gameTimeUTC"]="2026-11-08T23:00:00Z"
        result=collect_boxscores(DAY,fetch=lambda _:{"scoreboard":{"games":[prior]}},now=NOW)
        self.assertEqual(result["games"],[])

    def test_team_mismatch_fails_closed(self):
        def fetch(url):
            bad=box()
            bad["game"]["homeTeam"]["teamTricode"]="LAL"
            return {"scoreboard":{"games":[game()]}} if url in NBA_LIVE_URLS else bad
        result = collect_boxscores(DAY, fetch=fetch, now=NOW)
        self.assertEqual(result["games"], [])
        self.assertFalse(result["coverage"]["complete"])

    def test_wrong_id_cannot_escape_failover_and_other_game_survives(self):
        other = game()
        other["gameId"] = "0022600201"

        def fetch(url):
            if url in NBA_LIVE_URLS:
                return {"scoreboard": {"games": [game(), other]}}
            response = box()
            if url.endswith("0022600200.json"):
                response["game"]["gameId"] = "0022600999"
            else:
                response["game"]["gameId"] = other["gameId"]
            return response

        result = collect_boxscores(DAY, fetch=fetch, now=NOW)
        self.assertEqual(result["coverage"]["active_or_final_count"], 2)
        self.assertEqual(result["coverage"]["observed_game_count"], 1)
        self.assertEqual(result["status"], "PARTIAL_NBA_PLAYER_BOXSCORES")

    def test_malformed_primary_box_uses_valid_mirror(self):
        def fetch(url):
            if url in NBA_LIVE_URLS:
                return {"scoreboard": {"games": [game()]}}
            if url.startswith(BOX_BASES[0]):
                return {"game": {"gameId": "0022600200"}}
            return box()

        result = collect_boxscores(DAY, fetch=fetch, now=NOW)
        self.assertTrue(result["coverage"]["complete"])

    def test_failed_one_boxscore_does_not_claim_row(self):
        def fetch(url):
            if url in NBA_LIVE_URLS:return {"scoreboard":{"games":[game()]}}
            raise OSError("blocked")
        result=collect_boxscores(DAY,fetch=fetch,now=NOW)
        self.assertEqual(result["coverage"]["active_or_final_count"],1)
        self.assertEqual(result["coverage"]["observed_game_count"],0)
        self.assertEqual(result["status"],"PARTIAL_NBA_PLAYER_BOXSCORES")
        self.assertFalse(result["coverage"]["complete"])
        self.assertEqual(result["games"],[])

    def test_real_partial_player_totals_are_publishable_but_empty_partial_is_not(self):
        report={"status":"PARTIAL_NBA_PLAYER_BOXSCORES","games":[{"game":"BOS @ NYK","player_rows":[{"PTS":9}]}]}
        self.assertTrue(publishable_observations(report))
        self.assertFalse(publishable_observations({**report,"games":[]}))
        self.assertFalse(publishable_observations({"status":"NBA_PLAYER_BOXSCORES_UNAVAILABLE","games":[]}))

    def test_empty_official_pregame_feed_after_verified_tip_is_not_live_success(self):
        schedule={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"date_eastern":DAY.isoformat(),
                            "start":"2026-11-09T23:30:00Z"}]}
        self.assertTrue(verified_started(schedule,DAY,NOW+dt.timedelta(minutes=6)))
        self.assertFalse(verified_started(schedule,DAY,NOW+dt.timedelta(minutes=3)))
        self.assertFalse(verified_started({**schedule,"coverage_complete":False},DAY,NOW+dt.timedelta(minutes=6)))

    def test_previous_day_scoreboard_rejected(self):
        with self.assertRaises(ValueError):
            collect_boxscores(DAY,fetch=lambda _:{"scoreboard":{"gameDate":"2026-11-08","games":[]}},now=NOW)

    def test_verified_full_slate_before_tipoff_waits_without_fake_stats(self):
        schedule={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat(),
                           "start":"2026-11-10T00:00:00+00:00"}]}
        result=waiting_for_tipoff(schedule,DAY,now=NOW)
        self.assertEqual(result["status"],"WAITING_FOR_SCHEDULED_TIPOFF")
        self.assertIsNone(result["captured_at"])
        self.assertEqual(result["games"],[])
        self.assertFalse(result["coverage"]["complete"])

    def test_after_tipoff_must_attempt_live_data(self):
        schedule={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat(),
                           "start":"2026-11-09T20:00:00+00:00"}]}
        self.assertIsNone(waiting_for_tipoff(schedule,DAY,now=NOW))

    def test_incomplete_or_wrong_day_schedule_cannot_suppress_live_poll(self):
        base={"coverage_complete":False,"dates_eastern":[DAY.isoformat()],
              "games":[{"date_eastern":DAY.isoformat(),"start":"2026-11-10T00:00:00+00:00"}]}
        self.assertIsNone(waiting_for_tipoff(base,DAY,now=NOW))
        base["coverage_complete"]=True
        base["dates_eastern"]=["2026-11-08"]
        self.assertIsNone(waiting_for_tipoff(base,DAY,now=NOW))

    def test_s3_backup_scoreboard_is_attempted(self):
        seen=[]
        def fetch(url):
            seen.append(url)
            if url==NBA_LIVE_URLS[0]:raise OSError("blocked")
            return {"scoreboard":{"games":[]}}
        result=collect_boxscores(DAY,fetch=fetch,now=NOW)
        self.assertEqual(seen[:2],list(NBA_LIVE_URLS))
        self.assertEqual(result["games"],[])

if __name__=="__main__":
    unittest.main()

class PlayerCollectorCadenceTests(unittest.TestCase):
    def test_live_window_has_recovery_headroom_before_twenty_minute_expiry(self):
        import re
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[2] / '.github/workflows/independent_nba_player_boxscores.yml').read_text()
        crons = [c.split() for c in re.findall(r'cron: "([^"]+)"', workflow)]
        for hour in [23, *range(9)]:
            minutes = set()
            for c in crons:
                hours = set()
                for part in c[1].split(','):
                    if part == '*': hours.update(range(24))
                    elif '-' in part:
                        a,b=map(int,part.split('-'));hours.update(range(a,b+1))
                    else: hours.add(int(part))
                if hour in hours: minutes.update(map(int,c[0].split(',')))
            ordered=sorted(minutes)
            self.assertTrue(ordered)
            self.assertLessEqual(max(b-a for a,b in zip(ordered,ordered[1:]+[ordered[0]+60])),5)

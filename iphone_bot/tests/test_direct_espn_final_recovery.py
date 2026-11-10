import datetime as dt
import unittest

from iphone_bot.fetch_final_boxscores import (
    ESPN_BOX, ESPN_SCORE, NBA_BOX, NBA_SCOREBOARD, NBA_SCHEDULE,
    NBA_SCHEDULE_ALT, gather, verified_espn_schedule_hints,
    verified_direct_espn_summary,
)

GAME="Cleveland Cavaliers @ Charlotte Hornets"
WHEN="2026-11-10T00:00:00Z"
IDENT=("2026-11-09","CLE","CHA")
EVENT_ID="401909953"
NOW=dt.datetime.fromisoformat("2026-11-10T02:15:00+00:00")

def schedule():
    return {"status":"THIRD_PARTY_NBA_SCHEDULE_ONLY","games":[
        {"id":EVENT_ID,"game":GAME,"date_eastern":"2026-11-09",
         "start":WHEN,"away_abbreviation":"CLE","home_abbreviation":"CHA"}]}

def player():
    return {"athlete":{"displayName":"Sample Player"},"stats":["31:00","5","4","26"]}

def summary(*,completed=True,event_id=EVENT_ID,date=WHEN,away="CLE",home="CHA"):
    competitors=[
        {"homeAway":"away","team":{"abbreviation":away}},
        {"homeAway":"home","team":{"abbreviation":home}},
    ]
    return {"header":{"id":event_id,"competitions":[{
        "date":date,"competitors":competitors,
        "status":{"type":{"state":"post" if completed else "in",
                          "completed":completed}}
    }]},
    "boxscore":{"players":[{"team":{"abbreviation":away},
        "statistics":[{"names":["MIN","REB","AST","PTS"],
                       "athletes":[player()]}]}]}}

def pending():
    return [{"event_start":WHEN,"status":"PENDING","game":GAME,
             "team":"CLE","player_id":"123"}]

class DirectEspnFinalFallback(unittest.TestCase):
    def test_saved_schedule_only_provides_lookup_not_final_proof(self):
        self.assertEqual(verified_espn_schedule_hints(schedule()),{IDENT:EVENT_ID})
        self.assertEqual(verified_direct_espn_summary(EVENT_ID,IDENT,summary(completed=False)),[])
        self.assertEqual(verified_direct_espn_summary(EVENT_ID,IDENT,summary())[0]["PTS"],26)

    def test_rejects_mismatched_event_team_day_and_incomplete_status(self):
        for altered in (
            {"event_id":"999"}, {"away":"BOS"}, {"home":"MIA"},
            {"date":"2026-11-11T00:00:00Z"},
        ):
            with self.assertRaises(ValueError):
                verified_direct_espn_summary(EVENT_ID,IDENT,summary(**altered))
        s=summary()
        del s["header"]["competitions"][0]["status"]
        self.assertEqual(verified_direct_espn_summary(EVENT_ID,IDENT,s),[])

    def test_espn_dnp_requires_explicit_reason_and_no_minutes(self):
        record=summary()
        players=record["boxscore"]["players"][0]["statistics"][0]["athletes"]
        players.append({"athlete":{"displayName":"Explicit DNP"},
                        "didNotPlay":True,"reason":"Coach's Decision","stats":[]})
        players.append({"athlete":{"displayName":"Unverified DNP"},
                        "didNotPlay":True,"stats":[]})
        players.append({"athlete":{"displayName":"Contradictory Minutes"},
                        "didNotPlay":True,"reason":"DNP","stats":["12:30","0","0","0"]})
        rows=verified_direct_espn_summary(EVENT_ID,IDENT,record)
        dnps=[x for x in rows if x.get("dnp_final_verified")]
        self.assertEqual(len(dnps),1)
        self.assertEqual(dnps[0]["player"],"Explicit DNP")
        self.assertEqual(dnps[0]["dnp_reason"],"Coach's Decision")

    def test_direct_summary_bypasses_both_failed_scoreboards_and_season_schedule(self):
        called=[]
        def request(url):
            called.append(url)
            if url==NBA_SCOREBOARD:
                raise TimeoutError("NBA scoreboard down")
            if url==NBA_BOX.format("0022600204"):
                raise TimeoutError("NBA official box not yet available")
            if url.startswith(ESPN_BOX):
                return summary()
            if url in (NBA_SCHEDULE,NBA_SCHEDULE_ALT):
                raise AssertionError("Must not fetch slow season schedules after final ESPN summary")
            if url.startswith(ESPN_SCORE):
                raise AssertionError("Daily ESPN scoreboard unavailable but direct final works")
            raise AssertionError(url)
        rows,status=gather(pending(),now=NOW,request=request,
                           known_espn_games={IDENT:EVENT_ID},
                           known_game_ids=[{"date":"2026-11-09","away":"CLE","home":"CHA","game_id":"0022600204"}])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["source"],"ESPN_FINAL")
        self.assertEqual(status["direct_espn_final_games"],1)
        self.assertEqual(status["final_espn_games"],1)
        self.assertNotIn(NBA_SCHEDULE,called)
        self.assertFalse(any(x.startswith(ESPN_SCORE) for x in called))

    def test_inprogress_direct_summary_cannot_be_graded(self):
        def request(url):
            if url==NBA_SCOREBOARD:
                raise TimeoutError("NBA scoreboard down")
            if url.startswith(ESPN_BOX):
                return summary(completed=False)
            if url in (NBA_SCHEDULE,NBA_SCHEDULE_ALT):
                raise TimeoutError("season unavailable")
            if url.startswith(ESPN_SCORE):
                raise TimeoutError("ESPN scoreboard unavailable")
            raise AssertionError(url)
        rows,status=gather(pending(),now=NOW,request=request,known_espn_games={IDENT:EVENT_ID})
        self.assertEqual(rows,[])
        self.assertEqual(status["final_espn_games"],0)
        self.assertEqual(status["status"],"NO_FINAL_BOXSCORES_AVAILABLE")

if __name__=="__main__":unittest.main()

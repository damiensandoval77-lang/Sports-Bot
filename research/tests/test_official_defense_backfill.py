import copy
import unittest
from datetime import datetime,timezone,timedelta
from research.official_defense_backfill import collect,planned_games,MAX_GAMES

NOW=datetime(2026,11,11,4,0,tzinfo=timezone.utc)
GID="0022600123"
EVENT="2026-11-09T00:00:00+00:00"
DATE="2026-11-08"

def season():
    return {"status":"VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE",
        "season":"2026-27","generated_at":"2026-11-08T01:00:00+00:00",
        "source_url":"https://example.org/schedule",
        "games":[{"id":"401901234","start":EVENT,"date_eastern":DATE,
            "away_abbreviation":"BOS","home_abbreviation":"NYK"}]}

def official():
    return {"leagueSchedule":{"seasonYear":"2026-27",
        "gameDates":[{"gameDate":DATE,"games":[{"gameId":GID,
        "awayTeam":{"teamTricode":"BOS"},"homeTeam":{"teamTricode":"NYK"}}]}]}}

def final_box(status=3, away="BOS"):
    def t(team):
        return {"teamTricode":team, "score":sum(10+k for k in range(8)),
          "players":[{"name":team+str(k),"statistics":{
              "points":10+k,"reboundsTotal":4,"assists":2,"minutes":"25:00"}}
          for k in range(8)]}
    return {"game":{"gameId":GID,"gameStatus":status,
        "gameTimeUTC":EVENT,"awayTeam":t(away),"homeTeam":t("NYK")}}

def fetch(url):
    if "scheduleLeague" in url:return official()
    return final_box()

class OfficialBackfillTests(unittest.TestCase):
    def test_official_inactive_players_preserve_verified_final_box(self):
        def request(url):
            if "scheduleLeague" in url:return official()
            x=final_box()
            x["game"]["awayTeam"]["players"].append({
                "name":"Inactive Player", "status":"INACTIVE", "notPlayingReason":"INACTIVE_INJURY"})
            return x
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=request)
        self.assertEqual(result["verified_new_games"],1)
        self.assertEqual(result["verified_combined_games"],1)

    def test_real_final_identity_and_reciprocal_rows(self):
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=fetch)
        self.assertEqual(result["verified_new_games"],1)
        self.assertEqual(result["verified_combined_games"],1)
        self.assertEqual(len(result["rows"]),16)
        self.assertFalse(result["production_approved"])
        self.assertFalse(result["retroactive_pregame_feature_claims"])

    def test_not_final_game_rejected(self):
        def f(url):
            if "scheduleLeague" in url:return official()
            return final_box(status=2)
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=f)
        self.assertEqual(result["verified_new_games"],0)

    def test_wrong_team_rejected(self):
        def f(url):
            if "scheduleLeague" in url:return official()
            return final_box(away="LAL")
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=f)
        self.assertEqual(result["verified_new_games"],0)

    def test_wrong_game_id_rejected(self):
        def f(url):
            if "scheduleLeague" in url:return official()
            x=final_box()
            x["game"]["gameId"]="0022609999"
            return x
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=f)
        self.assertEqual(result["verified_new_games"],0)

    def test_postgame_no_tip_future_data(self):
        s=season()
        s["games"][0]["start"]="2026-11-11T23:00:00Z"
        s["games"][0]["date_eastern"]="2026-11-11"
        self.assertEqual(planned_games(s,NOW),[])

    def test_fresh_schedule_not_backdated(self):
        s=season()
        s["generated_at"]="2026-11-12T00:00:00Z"
        with self.assertRaises(ValueError):planned_games(s,NOW)

    def test_bounded_request_budget(self):
        with self.assertRaises(ValueError):planned_games(season(),NOW,limit=MAX_GAMES+1)

    def test_partial_box_rows_rejected(self):
        def f(url):
            if "scheduleLeague" in url:return official()
            x=final_box()
            x["game"]["awayTeam"]["players"]=x["game"]["awayTeam"]["players"][:3]
            return x
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=f)
        self.assertEqual(result["verified_new_games"],0)
        self.assertEqual(result["failures"].get("partial_or_inconsistent_final_box"),1)

    def test_corrupt_player_pra_or_invalid_minutes_never_create_valid_game(self):
        def f(url):
            if "scheduleLeague" in url:return official()
            x=final_box()
            x["game"]["homeTeam"]["players"][0]["statistics"]["minutes"]="bad"
            return x
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=f)
        # Missing malformed player row makes the official team totals disagree.
        self.assertEqual(result["verified_new_games"],0)
        self.assertEqual(len(result["rows"]),0)


def espn_summary(completed=True,home="NYK",game_id="401901234",score_adjust=0):
    teams=[("away","BOS"),("home",home)]
    comp={"date":EVENT,"status":{"type":{"completed":completed,"state":"post" if completed else "in"}},
          "competitors":[{"homeAway":side,"team":{"abbreviation":abbr},
                          "score":str(sum(10+k for k in range(8))+(score_adjust if side=="away" else 0))}
                         for side,abbr in teams]}
    return {"header":{"id":game_id,"competitions":[comp]},
            "boxscore":{"players":[{"team":{"abbreviation":abbr},
              "statistics":[{"names":["MIN","PTS","REB","AST"],
                             "athletes":[{"athlete":{"displayName":abbr+str(k)},
                                          "stats":["25:00",str(10+k),"4","2"]}
                                         for k in range(8)]}]}
             for _,abbr in teams]}}

def no_official_schedule_espn(url):
    if "scheduleLeague" in url:raise OSError("official endpoint unavailable")
    if "espn.com" in url:return espn_summary()
    raise ValueError("unexpected URL")


class ESPNBackfillTests(unittest.TestCase):
    def test_espn_final_fallback_when_official_schedule_down(self):
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=no_official_schedule_espn)
        self.assertEqual(result["verified_new_games"],1)
        self.assertEqual(result["verified_games_by_provider"],{"ESPN_FINAL":1})
        self.assertEqual(result["verified_combined_games"],1)
        self.assertEqual(len(result["rows"]),16)

    def test_espn_inprogress_fallback_rejected(self):
        def request(url):
            if "scheduleLeague" in url:raise OSError("blocked")
            return espn_summary(completed=False)
        self.assertEqual(collect(season(),{"version":1,"rows":[]},now=NOW,request=request)["verified_new_games"],0)

    def test_espn_identity_mismatch_rejected(self):
        def request(url):
            if "scheduleLeague" in url:raise OSError("blocked")
            return espn_summary(home="LAL")
        self.assertEqual(collect(season(),{"version":1,"rows":[]},now=NOW,request=request)["verified_new_games"],0)

    def test_espn_scoreboard_must_equal_player_totals(self):
        def request(url):
            if "scheduleLeague" in url:raise OSError("blocked")
            return espn_summary(score_adjust=3)
        result=collect(season(),{"version":1,"rows":[]},now=NOW,request=request)
        self.assertEqual(result["verified_new_games"],0)
        self.assertEqual(result["failures"]["partial_or_inconsistent_final_box"],1)

    def test_espn_wrong_game_id_rejected(self):
        def request(url):
            if "scheduleLeague" in url:raise OSError("blocked")
            return espn_summary(game_id="9999")
        self.assertEqual(collect(season(),{"version":1,"rows":[]},now=NOW,request=request)["verified_new_games"],0)


class ProviderCircuitBreakerTests(unittest.TestCase):
    def test_fails_closed_after_three_provider_http_errors(self):
        from urllib.error import HTTPError
        s=season()
        games=[]
        for i in range(9):
            g=dict(s["games"][0])
            g["id"]=str(401901234+i)
            g["start"]=(datetime(2026,11,1+i,0,0,tzinfo=timezone.utc)).isoformat()
            g["date_eastern"]=(datetime(2026,10,31,tzinfo=timezone.utc)+timedelta(days=i)).date().isoformat()
            games.append(g)
        s["games"]=games
        now=datetime(2026,11,11,4,0,tzinfo=timezone.utc)
        attempts=[]
        def request(url):
            attempts.append(url)
            if "scheduleLeague" in url:raise OSError("NBA schedule unavailable")
            raise HTTPError(url,403,"blocked",None,None)
        result=collect(s,{"version":1,"rows":[]},now=now,request=request)
        self.assertTrue(result["espn_http_circuit_open"])
        self.assertEqual(result["failures"]["espn_box_HTTPError"],3)
        self.assertGreater(result["failures"]["espn_skipped_circuit_open"],0)
        self.assertEqual(result["verified_new_games"],0)
        self.assertFalse(result["production_approved"])

if __name__=="__main__":unittest.main()

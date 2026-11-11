import copy
import unittest
from datetime import datetime,timezone
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
        self.assertEqual(result["failures"].get("partial_official_final_box"),1)

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

if __name__=="__main__":unittest.main()

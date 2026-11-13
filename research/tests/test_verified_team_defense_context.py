"""No inferred defense versus position or future-game leakage."""
import copy
import unittest
from research.verified_team_defense_context import final_games,build

LOCK="2026-11-11T20:00:00Z"

def rows(gid,day,one="BOS",two="NYK",num=8):
    out=[]
    for t,opp in ((one,two),(two,one)):
        for n in range(num):
            p,r,a=n+5,n+2,n
            out.append({"source_game_id":gid,"date":day,"player":t+str(n),
                "team":t,"opponent":opp,"PTS":p,"REB":r,"AST":a,"PRA":p+r+a,
                "source":"NBA_CDN_FINAL","final_confirmed":True})
    return out

def schedule():
    return {"generated_at":"2026-11-11T19:00:00Z",
            "source_url":"https://example.org/schedule",
            "games":[{"id":"next","start":"2026-11-12T00:00:00Z",
                      "date_eastern":"2026-11-11","home_abbreviation":"BOS",
                      "away_abbreviation":"NYK"}]}

def cache(n=5):
    return {"version":1,"rows":sum([rows(str(x),f"2026-11-{x+1:02d}") for x in range(n)],[])}

class TeamDefenseTests(unittest.TestCase):
    def test_short_rotation_requires_precise_official_full_game_minutes(self):
        for n in (5, 6):
            c={"version":1,"rows":rows("short","2026-11-01",num=n)}
            for r in c["rows"]:r["MIN"]=240/n
            self.assertEqual(len(final_games(c)[0]),1)
            c["rows"][0]["MIN"]-=1
            self.assertEqual(final_games(c)[1],{"partial_boxscore":1})

    def test_rounded_or_missing_minutes_do_not_certify_short_rotation(self):
        for change in ({"MIN":None},{"MIN":40,"source":"ESPN_FINAL"},{"MIN":float("nan")}):
            c={"version":1,"rows":rows("short","2026-11-01",num=6)}
            for r in c["rows"]:r["MIN"]=40
            c["rows"][0].update(change)
            self.assertEqual(final_games(c)[1],{"partial_boxscore":1})

    def test_verified_dnp_without_totals_does_not_discard_complete_game(self):
        c=cache(1)
        c["rows"].append({"source_game_id":"0", "date":"2026-11-01",
            "player":"DNP player", "team":"BOS", "opponent":"NYK",
            "source":"NBA_CDN_FINAL", "final_confirmed":True,
            "dnp_final_verified":True, "dnp_reason":"INACTIVE_INJURY"})
        games,rejected=final_games(c)
        self.assertEqual(len(games),1)
        self.assertEqual(rejected,{})
        self.assertEqual(games[0]["players_by_team"],{"BOS":8,"NYK":8})
        self.assertEqual(games[0]["totals"]["BOS"]["PTS"],68)

    def test_dnp_cannot_fill_missing_played_players(self):
        c={"version":1,"rows":rows("0","2026-11-01",num=6)}
        for team,opp in [("BOS","NYK"),("NYK","BOS")]:
            c["rows"].append({"source_game_id":"0", "date":"2026-11-01",
                "player":team+"DNP", "team":team,"opponent":opp,
                "source":"NBA_CDN_FINAL", "final_confirmed":True,
                "dnp_final_verified":True,"dnp_reason":"INACTIVE"})
        self.assertEqual(final_games(c)[1],{"partial_boxscore":1})

    def test_contradictory_or_unexplained_dnp_invalidates_game(self):
        for change in [{"PTS":3},{"MIN":12},{"dnp_reason":""}]:
            c=cache(1)
            c["rows"].append({"source_game_id":"0","date":"2026-11-01",
                "player":"DNP", "team":"BOS","opponent":"NYK",
                "source":"NBA_CDN_FINAL","final_confirmed":True,
                "dnp_final_verified":True,"dnp_reason":"INACTIVE",**change})
            self.assertEqual(len(final_games(c)[0]),0)

    def test_true_reciprocal_prior_team_totals(self):
        x=build(cache(),schedule(),frozen_at=LOCK)
        self.assertEqual(x["verified_final_games"],5)
        self.assertEqual(x["future_game_count"],1)
        d=x["future_games"][0]["team_defense"]["NYK"]
        self.assertEqual(d["status"],"VERIFIED_PRIOR_TEAM_TOTALS_ONLY")
        self.assertEqual(len(d["prior_game_ids"]),5)
        self.assertFalse(d["position_adjustment_verified"])
        self.assertFalse(x["production_hit_estimate_eligible"])

    def test_incomplete_boxscore_not_accepted(self):
        c=cache()
        c["rows"]=[r for r in c["rows"] if r["team"]!="NYK"]
        self.assertEqual(len(final_games(c)[0]),0)

    def test_conflicting_opponent_rejected(self):
        c=cache()
        c["rows"][0]["opponent"]="MIA"
        self.assertEqual(len(final_games(c)[0]),4)

    def test_duplicate_player_identifiers_rejected(self):
        c=cache()
        c["rows"].append(copy.deepcopy(c["rows"][0]))
        self.assertEqual(len(final_games(c)[0]),4)

    def test_nonfinal_rows_not_counted(self):
        c=cache()
        for r in c["rows"][:16]:r["final_confirmed"]=False
        self.assertEqual(len(final_games(c)[0]),4)

    def test_insufficient_games_explicit_unavailable(self):
        x=build(cache(3),schedule(),frozen_at=LOCK)
        self.assertEqual(x["future_games"][0]["team_defense"]["BOS"]["status"],
                         "INSUFFICIENT_VERIFIED_PRIOR_GAMES")
        self.assertEqual(x["blockers"]["insufficient_verified_prior_defense_games"],2)

    def test_future_game_data_cannot_be_used(self):
        c=cache(4)
        c["rows"]+=rows("future","2026-11-11")
        x=build(c,schedule(),frozen_at=LOCK)
        self.assertEqual(x["future_games"][0]["team_defense"]["BOS"]["observed_games"],4)

    def test_old_started_fixture_not_recomputed(self):
        s=schedule()
        s["games"][0]["start"]="2026-11-11T01:00:00Z"
        s["games"][0]["date_eastern"]="2026-11-10"
        x=build(cache(),s,frozen_at=LOCK)
        self.assertEqual(x["future_game_count"],0)

    def test_future_schedule_source_rejected(self):
        s=schedule()
        s["generated_at"]="2026-11-11T21:00:00Z"
        with self.assertRaises(ValueError):build(cache(),s,frozen_at=LOCK)

    def test_provenance_not_automatically_historical(self):
        x=build(cache(),schedule(),frozen_at=LOCK)
        self.assertIsNone(x["source_cache_published_at"])
        self.assertFalse(x["retroactive_feature_backfill_allowed"])
        self.assertFalse(x["cache_publication_time_verified"])

    def test_invalid_stat_and_pra_rejected(self):
        c=cache()
        c["rows"][0]["PRA"]=999
        self.assertEqual(len(final_games(c)[0]),4)

if __name__=="__main__":unittest.main()

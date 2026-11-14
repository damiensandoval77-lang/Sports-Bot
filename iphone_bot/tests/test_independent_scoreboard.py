import datetime as dt
import unittest
from iphone_bot.refresh_independent_scoreboard import snapshot, nba_live_scoreboard, NBA_LIVE_URLS, started_games_missing_scores

UTC=dt.timezone.utc
NOW=dt.datetime(2026,11,9,12,tzinfo=UTC)
DAY=dt.date(2026,11,9)

def event(id="123"):
    return {"id":id,"date":"2026-11-09T23:00:00Z",
            "competitions":[{"competitors":[
                {"homeAway":"home","team":{"displayName":"Home","abbreviation":"HOM"},"score":"0"},
                {"homeAway":"away","team":{"displayName":"Away","abbreviation":"AWY"},"score":"0"}]}],
            "status":{"type":{"state":"pre"}}}

class IndependentScoreboardTests(unittest.TestCase):
    def test_fetches_schedule_and_labels_not_odds(self):
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW)
        self.assertEqual(r["total_games"],1)
        self.assertEqual(r["status"],"OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES")
        self.assertFalse(r["is_sportsbook_feed"])
        self.assertFalse(r["is_prizepicks_feed"])

    def test_no_games_is_valid_when_provider_responds(self):
        r=snapshot([DAY],reader=lambda _: [],now=NOW)
        self.assertEqual(r["total_games"],0)
        self.assertIsNone(r["error"])

    def test_failure_keeps_old_capture_time(self):
        prior={"generated_at":"2026-11-09T10:00:00+00:00","games":[{"id":"old"}],"total_games":1}
        def fail(_): raise OSError("network unavailable")
        r=snapshot([DAY],reader=fail,now=NOW,previous=prior)
        self.assertEqual(r["status"],"STALE_UPSTREAM_ERROR")
        self.assertEqual(r["generated_at"],prior["generated_at"])
        self.assertEqual(r["games"],prior["games"])

    def test_failure_without_history_never_marks_fresh(self):
        def fail(_): raise TimeoutError("timeout")
        r=snapshot([DAY],reader=fail,now=NOW)
        self.assertEqual(r["status"],"UNAVAILABLE_UPSTREAM_ERROR")
        self.assertIsNone(r["generated_at"])

    def test_duplicate_dates_fail_closed(self):
        r=snapshot([DAY,DAY],reader=lambda _: [event()],now=NOW)
        self.assertEqual(r["status"],"UNAVAILABLE_UPSTREAM_ERROR")


    def test_empty_provider_response_rejected_if_schedule_has_games(self):
        baseline={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat()}]}
        r=snapshot([DAY],reader=lambda _: [],now=NOW,schedule=baseline)
        self.assertEqual(r["status"],"UNAVAILABLE_UPSTREAM_ERROR")
        self.assertIsNone(r["generated_at"])

    def test_provider_missing_one_matchup_retains_previous(self):
        baseline={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat()},
                           {"game":"Other @ Other Home","date_eastern":DAY.isoformat()}]}
        prior={"generated_at":"2026-11-09T10:00:00+00:00",
               "games":[{"id":"saved"}],"total_games":1}
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW,
                   previous=prior,schedule=baseline)
        self.assertEqual(r["status"],"STALE_UPSTREAM_ERROR")
        self.assertEqual(r["generated_at"],prior["generated_at"])

    def test_espn_http_200_missing_official_game_uses_full_fallback(self):
        baseline={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat()},
                           {"game":"Washington Wizards @ Detroit Pistons","date_eastern":DAY.isoformat()}]}
        def fallback(_):
            return {"events":[{"id":"123","game":"Away @ Home",
                    "date_eastern":DAY.isoformat(),"start":"2026-11-09T23:00:00Z"},
                    {"id":"0022600205","game":"Washington Wizards @ Detroit Pistons",
                    "date_eastern":DAY.isoformat(),"start":"2026-11-10T00:00:00Z"}],
                    "source":"Previously verified NBA schedule cache (NOT live scores)"}
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW,
                   schedule=baseline,fallback=fallback)
        self.assertEqual(r["total_games"],2)
        self.assertEqual(r["status"],"NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE")
        self.assertFalse(r["is_live_score_source"])

    def test_complete_provider_matches_known_slate(self):
        baseline={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat()}]}
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW,schedule=baseline)
        self.assertEqual(r["total_games"],1)
        self.assertEqual(r["status"],"OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES")

    def test_incomplete_schedule_not_used_as_coverage_assertion(self):
        baseline={"coverage_complete":False,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Other @ Other Home","date_eastern":DAY.isoformat()}]}
        r=snapshot([DAY],reader=lambda _: [event()],now=NOW,schedule=baseline)
        self.assertEqual(r["status"],"OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES")


    def test_espn_http_failure_uses_independent_nba_schedule(self):
        def blocked(_): raise OSError("ESPN unavailable")
        def backup(_):
            return {"events":[{"id":"nba-1","game":"Away @ Home",
                     "date_eastern":DAY.isoformat(),"game_state":"pre",
                     "start":"2026-11-09T23:00:00+00:00"}],
                    "source":"NBA public CDN season schedule","rejected":0}
        r=snapshot([DAY],reader=blocked,fallback=backup,now=NOW)
        self.assertEqual(r["status"],"NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE")
        self.assertFalse(r["is_live_score_source"])
        self.assertEqual(r["total_games"],1)

    def test_both_sources_fail_produces_explicit_unavailable_status(self):
        def blocked(_): raise OSError("ESPN unavailable")
        def failed(_): raise RuntimeError("NBA CDN unavailable")
        r=snapshot([DAY],reader=blocked,fallback=failed,now=NOW)
        self.assertEqual(r["status"],"UNAVAILABLE_UPSTREAM_ERROR")
        self.assertIsNone(r["generated_at"])


    def test_nba_live_cdn_scoreboard_parses_real_score_pair(self):
        def response(_):
            return {"scoreboard":{"games":[
                {"gameId":"0022600001","gameDateTimeUTC":"2026-11-09T23:00:00Z",
                 "gameStatus":2,"period":2,
                 "awayTeam":{"teamCity":"Away","teamName":"Team","teamTricode":"AWY","score":53},
                 "homeTeam":{"teamCity":"Home","teamName":"Team","teamTricode":"HOM","score":58}}
            ]}}
        result=nba_live_scoreboard([DAY],requester=response)
        self.assertEqual(result["events"][0]["away_score"],53)
        self.assertEqual(result["events"][0]["home_score"],58)
        self.assertEqual(result["events"][0]["game_state"],"in")

    def test_stale_espn_schedule_after_tipoff_tries_real_live_fallback(self):
        now=dt.datetime(2026,11,10,0,30,tzinfo=UTC)
        schedule={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat(),
                            "start":"2026-11-10T00:00:00Z"}]}
        calls=[]
        def fallback(_):
            calls.append(True)
            return {"events":[{"id":"nba-verified","game":"Away @ Home",
                "date_eastern":DAY.isoformat(),"start":"2026-11-10T00:00:00Z",
                "game_state":"in","home_score":43,"away_score":41}],
                "source":"NBA official liveData scoreboard via NBA CDN"}
        r=snapshot([DAY],reader=lambda _: [event()],schedule=schedule,now=now,fallback=fallback)
        self.assertEqual(len(calls),1)
        self.assertEqual(r["status"],"OBSERVED_NBA_LIVE_SCOREBOARD")
        self.assertEqual(r["games"][0]["home_score"],43)

    def test_stale_espn_and_stale_live_fallback_fail_closed(self):
        now=dt.datetime(2026,11,10,0,30,tzinfo=UTC)
        schedule={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat(),
                            "start":"2026-11-10T00:00:00Z"}]}
        def stale(_):
            return {"events":[{"id":"nba-verified","game":"Away @ Home",
                "date_eastern":DAY.isoformat(),"start":"2026-11-10T00:00:00Z",
                "game_state":"pre","home_score":None,"away_score":None}],
                "source":"NBA official liveData scoreboard via NBA CDN"}
        r=snapshot([DAY],reader=lambda _: [event()],schedule=schedule,now=now,
                   fallback=stale,previous={"generated_at":"2026-11-09T17:00:00Z",
                      "games":[{"id":"old"}]})
        self.assertEqual(r["status"],"STALE_UPSTREAM_ERROR")
        self.assertEqual(r["generated_at"],"2026-11-09T17:00:00Z")

    def test_post_tip_grace_does_not_require_immediate_live_scores(self):
        schedule={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat(),
                            "start":"2026-11-10T00:00:00Z"}]}
        rows=[{"game":"Away @ Home","date_eastern":DAY.isoformat(),
               "game_state":"pre","home_score":None,"away_score":None}]
        now=dt.datetime(2026,11,10,0,5,tzinfo=UTC)
        self.assertFalse(started_games_missing_scores(rows,schedule,[DAY],now))
        self.assertTrue(started_games_missing_scores(
            rows,schedule,[DAY],now+dt.timedelta(minutes=10)))

    def test_s3_fallback_after_nba_cdn_http_error(self):
        visited=[]
        def response(url):
            visited.append(url)
            if url==NBA_LIVE_URLS[0]:raise OSError("403")
            return {"scoreboard":{"games":[]}}
        r=nba_live_scoreboard([DAY],requester=response)
        self.assertEqual(visited,list(NBA_LIVE_URLS))
        self.assertIn("mediaops S3",r["source"])

    def test_both_live_sources_fail_without_false_scores(self):
        def fail(_):raise OSError("blocked")
        with self.assertRaises(RuntimeError):
            nba_live_scoreboard([DAY],requester=fail)

    def test_http_success_with_rejected_rows_tries_second_live_source(self):
        visited=[]
        decisions=iter([False,True])
        def response(url):
            visited.append(url)
            return {"scoreboard":{"games":[]}}
        result=nba_live_scoreboard([DAY],requester=response,
                                  validate_rows=lambda rows:next(decisions))
        self.assertEqual(visited,list(NBA_LIVE_URLS))
        self.assertIn('mediaops S3',result['source'])

    def test_both_http_successes_with_stale_rows_fail_closed(self):
        with self.assertRaises(RuntimeError):
            nba_live_scoreboard([DAY],requester=lambda url:{'scoreboard':{'games':[]}},
                               validate_rows=lambda rows:False)


    def test_cached_dated_schedule_cannot_be_called_live(self):
        baseline={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],
                  "games":[{"game":"Away @ Home","date_eastern":DAY.isoformat()}]}
        def blocked(_):raise OSError("blocked")
        def cached(_):
            return {"events":[{"id":"123","game":"Away @ Home","date_eastern":DAY.isoformat(),
                    "start":"2026-11-09T23:00:00Z","game_state":"pre",
                    "away_score":None,"home_score":None}],
                    "source":"Previously verified NBA schedule cache (NOT live scores)"}
        r=snapshot([DAY],reader=blocked,fallback=cached,now=NOW,schedule=baseline)
        self.assertEqual(r["status"],"NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE")
        self.assertFalse(r["is_live_score_source"])
        self.assertEqual(r["total_games"],1)


class PartialCurrentScoreTests(unittest.TestCase):
    def test_valid_peer_survives_failed_fallback_without_old_scores(self):
        now=dt.datetime(2026,11,10,0,30,tzinfo=UTC)
        live=event("live")
        live["status"]["type"]["state"]="in"
        live["competitions"][0]["competitors"][0]["score"]="51"
        live["competitions"][0]["competitors"][1]["score"]="49"
        missing={"game":"Missing @ Matchup", "date_eastern":DAY.isoformat(),"start":"2026-11-10T00:00:00Z"}
        schedule={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],"games":[missing]}
        def fail(_):raise RuntimeError("upstream unavailable")
        old={"generated_at":"2026-11-09T20:00:00Z","games":[{**missing,"home_score":20,"away_score":21}]}
        out=snapshot([DAY],reader=lambda _: [live],fallback=fail,schedule=schedule,now=now,previous=old)
        self.assertEqual(out["error"],"PARTIAL_CURRENT_SCOREBOARD")
        self.assertEqual(out["generated_at"],now.isoformat())
        self.assertEqual(out["games"][0]["home_score"],51)
        self.assertEqual(len(out["games"]),1)
        self.assertNotIn(missing,out["games"])

    def test_partial_delayed_pregame_is_unknown_and_scoreless(self):
        from iphone_bot.refresh_independent_scoreboard import salvage_current_scores
        now=dt.datetime(2026,11,10,0,30,tzinfo=UTC)
        delayed={"id":"d","game":"D @ E","date_eastern":DAY.isoformat(),"start":"2026-11-10T00:00:00Z","game_state":"pre","home_score":0,"away_score":0}
        live={"id":"a","game":"A @ B","date_eastern":DAY.isoformat(),"game_state":"in","home_score":12,"away_score":14}
        schedule={"coverage_complete":True,"dates_eastern":[DAY.isoformat()],"games":[delayed]}
        out=salvage_current_scores({"games":[live,delayed]},[DAY],schedule,now)
        self.assertEqual(out["games"][1]["game_state"],"unknown")
        self.assertIsNone(out["games"][1]["home_score"])
        self.assertEqual(out["games"][0]["home_score"],12)

    def test_no_valid_current_score_does_not_restamp_prior(self):
        from iphone_bot.refresh_independent_scoreboard import salvage_current_scores
        for rows in ([{"id":"a","date_eastern":DAY.isoformat(),"game":"A @ B","game_state":"pre"}], [None]):
            self.assertIsNone(salvage_current_scores({"games":rows},[DAY],{},NOW))

    def test_duplicate_fixture_rejected(self):
        from iphone_bot.refresh_independent_scoreboard import salvage_current_scores
        row={"id":"a","date_eastern":DAY.isoformat(),"game":"A @ B","game_state":"in","home_score":2,"away_score":2}
        self.assertIsNone(salvage_current_scores({"games":[row,{**row,"id":"b"}]},[DAY],{},NOW))

if __name__=="__main__":
    unittest.main()

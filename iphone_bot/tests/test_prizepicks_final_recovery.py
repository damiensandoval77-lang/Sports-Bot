import datetime as dt
import unittest
from unittest.mock import patch

from iphone_bot.recover_prizepicks_final_games import pending_matchup_requests, recover, multi_origin_request, S3_BASE
from iphone_bot.prizepicks_research_ledger import settle

NOW=dt.datetime(2026,11,9,14,tzinfo=dt.timezone.utc)

def research(status="PENDING",name="Test Player"):
    return {"status":status,"start":"2026-11-09T00:00:00Z",
            "game":"Los Angeles Lakers @ Detroit Pistons","team":"LAL",
            "player_id":"12345","player":name,"stat":"PTS","line":18.5,
            "combined_projection":21.5}

def verified(name="Test Player",pts=24):
    return {"player":name,"team":"LAL","opponent":"DET",
            "date":"2026-11-08","source":"NBA_CDN_FINAL","source_game_id":"0022600009",
            "final_confirmed":True,"PTS":pts,"REB":4,"AST":2,"PRA":pts+6,"MIN":30}

class RecoveryTests(unittest.TestCase):
    def test_deduplicates_thresholds_for_final_fetch(self):
        rows=[research(),{**research(),"line":21.5}]
        result=pending_matchup_requests(rows,now=NOW)
        self.assertEqual(len(result),1)

    def test_does_not_fetch_not_yet_final_games(self):
        row={**research(),"start":"2026-11-09T13:00:00Z"}
        self.assertEqual(pending_matchup_requests([row],now=NOW),[])

    def test_checked_official_final_settles_existing_forecast_without_rerun(self):
        row=research()
        result=settle({"records":[row]},[],now=NOW,final_games=[verified()])
        self.assertEqual(result["records"][0]["status"],"SETTLED")
        self.assertEqual(result["records"][0]["actual"],24)
        self.assertEqual(result["records"][0]["result"],"WIN")
        self.assertEqual(result["records"][0]["settlement_source"],"NBA_CDN_FINAL")
        self.assertEqual(result["records"][0]["combined_projection"],21.5)

    def test_wrong_player_or_opponent_cannot_grade(self):
        for final in [verified(name="Different Player"),{**verified(),"opponent":"BOS"}]:
            self.assertEqual(settle({"records":[research()]},[],now=NOW,final_games=[final])
                             ["records"][0]["status"],"PENDING")

    def test_ambiguous_duplicate_final_player_cannot_grade(self):
        final=verified()
        result=settle({"records":[research()]},[],now=NOW,final_games=[final,{**final,"source_game_id":"0022600010"}])
        self.assertEqual(result["records"][0]["status"],"PENDING")

    def test_nonfinal_or_untrusted_rows_cannot_grade(self):
        for final in [{**verified(),"final_confirmed":False},
                      {**verified(),"source":"UNVERIFIED_WEB"},
                      {**verified(),"dnp_final_verified":True}]:
            self.assertEqual(settle({"records":[research()]},[],now=NOW,final_games=[final])
                             ["records"][0]["status"],"PENDING")

    def test_recover_only_uses_actual_confirmed_boxscores(self):
        sample=research()
        def provider(url):
            # No provider hit on schedule that is not confirmed completed
            if "todaysScoreboard" in url:
                return {"scoreboard":{"games":[]}}
            raise OSError("no corroborated final")
        rows,status=recover([sample],now=NOW,request=provider)
        self.assertEqual(rows,[])
        self.assertEqual(status["verified_rows"],0)

    def test_saved_espn_ids_reach_automatic_recovery_without_provider_charges(self):
        row=research()
        expected={("2026-11-08","LAL","DET"):"401909001"}
        with patch("iphone_bot.recover_prizepicks_final_games.archived_espn_hints",
                   return_value=expected) as archive, patch(
                   "iphone_bot.recover_prizepicks_final_games.gather",
                   return_value=([verified()],{"status":"FINAL_BOXSCORES_FOUND"})
                   ) as fetch:
            rows,status=recover([row],now=NOW)
        archive.assert_called_once_with(dates={"2026-11-08"})
        self.assertEqual(fetch.call_args.kwargs["known_espn_games"],expected)
        self.assertEqual(status["archived_espn_game_id_hints"],1)
        self.assertEqual(status["verified_rows"],1)
        self.assertEqual(rows[0]["source"],"NBA_CDN_FINAL")

    def test_official_s3_scoreboard_first_and_nba_cdn_backup(self):
        from iphone_bot.fetch_final_boxscores import NBA_SCOREBOARD
        seen=[]
        def fake(url,timeout=7):
            seen.append(url)
            if url.startswith(S3_BASE):raise OSError("S3 unavailable")
            return {"scoreboard":{"games":[]}}
        result=multi_origin_request(NBA_SCOREBOARD,requester=fake)
        self.assertEqual(result["scoreboard"]["games"],[])
        self.assertEqual(seen[0],S3_BASE+"scoreboard/todaysScoreboard_00.json")
        self.assertEqual(seen[1],NBA_SCOREBOARD)

    def test_espn_summary_failover_preserves_event_id(self):
        from urllib.error import HTTPError
        from iphone_bot.fetch_final_boxscores import ESPN_BOX
        request = ESPN_BOX + "?event=401909960"
        mirror = request.replace("site.api.espn.com", "site.web.api.espn.com")
        seen = []

        def provider(url, timeout=7):
            seen.append(url)
            if url == request:
                raise HTTPError(url, 403, "Forbidden", {}, None)
            return {"header": {"id": "401909960"}}

        self.assertEqual(multi_origin_request(request, requester=provider)["header"]["id"], "401909960")
        self.assertEqual(seen, [request, mirror])

    def test_mediaops_official_boxscore_path_and_safe_failure(self):
        from iphone_bot.fetch_final_boxscores import NBA_BOX
        url=NBA_BOX.format("0022600009")
        seen=[]
        def fake(candidate,timeout=7):
            seen.append(candidate)
            raise OSError("offline")
        with self.assertRaises(OSError):
            multi_origin_request(url,requester=fake)
        self.assertEqual(seen[0],S3_BASE+"boxscore/boxscore_0022600009.json")
        self.assertEqual(seen[1],url)

    def test_verified_nba_final_inactive_player_is_void_not_under(self):
        final={**verified(),"PTS":None,"REB":None,"AST":None,"PRA":None,
               "MIN":None,"dnp_final_verified":True,
               "dnp_reason":"INACTIVE"}
        row=research()
        result=settle({"records":[row]},[],now=NOW,final_games=[final])["records"][0]
        self.assertEqual(result["status"],"VOID_DNP")
        self.assertEqual(result["result"],"VOID")
        self.assertIsNone(result["actual"])
        self.assertEqual(result["settlement_source"],"NBA_CDN_FINAL")

    def test_missing_player_is_not_automatically_void(self):
        result=settle({"records":[research()]},[],now=NOW,
                      final_games=[verified(name="Another Player")])["records"][0]
        self.assertEqual(result["status"],"PENDING")

    def test_unverified_dnp_reason_cannot_void(self):
        final={**verified(),"dnp_final_verified":True,"dnp_reason":None}
        result=settle({"records":[research()]},[],now=NOW,final_games=[final])["records"][0]
        self.assertEqual(result["status"],"PENDING")

    def test_old_games_excluded_from_bounded_automatic_retry(self):
        row={**research(),"start":"2026-11-01T00:00:00Z"}
        self.assertEqual(pending_matchup_requests([row],now=NOW),[])

if __name__=="__main__":
    unittest.main()

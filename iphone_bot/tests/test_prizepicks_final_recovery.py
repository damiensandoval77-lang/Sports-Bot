import datetime as dt
import unittest

from iphone_bot.recover_prizepicks_final_games import pending_matchup_requests, recover
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

    def test_old_games_excluded_from_bounded_automatic_retry(self):
        row={**research(),"start":"2026-11-01T00:00:00Z"}
        self.assertEqual(pending_matchup_requests([row],now=NOW),[])

if __name__=="__main__":
    unittest.main()

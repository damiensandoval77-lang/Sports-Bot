import gzip
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from iphone_bot.research_archive_persistence import preserve
from iphone_bot.research_storage_integrity import audit
from iphone_bot.capture_live_research import capture,save,players

AT=datetime(2026,11,8,1,30,tzinfo=timezone.utc)
TIP="2026-11-08T01:00:00Z"
BEFORE="2026-11-07T22:00:00Z"

def board():
    return {"status":"FROZEN_PREGAME_HISTORICAL_ARCHIVE_NOT_LIVE",
        "date_eastern":"2026-11-07",
        "original_board_generated_at":BEFORE,
        "comparisons":[{
          "player":"Nikola Jokic","player_id":"203999","team":"DEN",
          "game":"Denver Nuggets @ Indiana Pacers","start":TIP,
          "stat":"PTS","line":25.5,"projection":26.8,
          "combined_projection":27.5,
          "book_quotes":[{"name":"FanDuel","line":25.5,"over":-110,"under":-110}]}]}

def offer():
    return {"player":"Nikola Jokic","player_id":"203999","team":"DEN",
      "game":"Denver Nuggets @ Indiana Pacers","event_start":TIP,
      "captured_at":"2026-11-07T23:00:00Z","market":"PTS",
      "bookmaker":"FanDuel","line":25.5,"status":"PENDING",
      "combined_projection":27.5}

def scoreboard():
    return {"events":[{"id":"401909900",
      "competitions":[{"competitors":[
         {"homeAway":"away","team":{"displayName":"Denver Nuggets"}},
         {"homeAway":"home","team":{"displayName":"Indiana Pacers"}}]}],
      "status":{"type":{"state":"in"},"period":2,"displayClock":"5:11"}}]}

def summary(correct=True):
    return {"header":{"competitions":[{"competitors":[
        {"homeAway":"away","team":{"displayName":"Denver Nuggets"}},
        {"homeAway":"home","team":{"displayName":"Indiana Pacers" if correct else "Boston Celtics"}}]}]},
      "boxscore":{"players":[{"team":{"abbreviation":"DEN"},
       "statistics":[{"labels":["MIN","PTS","REB","AST"],
          "athletes":[{"athlete":{"id":"203999","displayName":"Nikola Jokic"},
            "stats":["16","14","6","7"]}]}]}]}}

class DurableResearchTests(unittest.TestCase):
    def test_archive_is_lossless_gz_and_immutable_on_second_run(self):
        with tempfile.TemporaryDirectory() as t:
            path,created=preserve(board(),t)
            self.assertTrue(created)
            self.assertEqual(json.loads(gzip.decompress(path.read_bytes())),board())
            again,new=preserve(board(),t)
            self.assertEqual(again,path)
            self.assertFalse(new)
            self.assertTrue(str(path).endswith(".json.gz"))

    def test_reject_posttip_archive(self):
        x=board()
        x["original_board_generated_at"]="2026-11-08T01:10:00Z"
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):preserve(x,t)

    def test_paper_and_archive_evidence_counted_separately(self):
        info=audit({"records":[offer()]},board(),
            {"coverage_complete":False,"games":[{"game":offer()["game"],
              "date_eastern":"2026-11-07"}]},
            {"locked_samples":2,"unified_reliability_v1":{
              "independent_research_markets":2,"data_availability":{
                "sanity_shadow_v1_missing":2,"stress_test_20k_v1_missing":2}}},
            now=datetime(2026,11,8,0,30,tzinfo=timezone.utc))
        self.assertEqual(info["saved_paper_quotes"],1)
        self.assertEqual(info["archive"]["archived_bookmaker_quotes"],1)
        self.assertEqual(info["archive"]["matched_existing_paper_quote_keys"],1)
        self.assertEqual(info["slate"]["scheduled_games_with_any_saved_paper_offer"],1)
        self.assertEqual(info["research_diagnostics"]["missing_sanity"],2)
        self.assertFalse(info["intermediate_live_player_stats_persisted"])

    def test_archive_only_offer_mismatch_is_preserved_without_grading(self):
        x=board()
        # Different line from the exact paper capture, same game and book.
        x["comparisons"][0]["book_quotes"][0]["line"]=26.5
        result=audit({"records":[offer()]},x,{"games":[]},{},
            now=datetime(2026,11,8,0,30,tzinfo=timezone.utc))
        a=result["archive"]
        self.assertEqual(a["archived_offers_not_found_in_paper"],1)
        self.assertEqual(a["archived_offer_mismatch_categories"]["PLAYER_MARKET_AND_BOOK_SAVED_DIFFERENT_LINE"],1)
        self.assertFalse(a["archive_only_offers_eligible_for_retroactive_grading"])

    def test_missing_paper_quote_reported_not_fabricated(self):
        info=audit({"records":[]},board(),{"games":[]},{},
            now=datetime(2026,11,8,0,30,tzinfo=timezone.utc))
        self.assertEqual(info["archive"]["archived_offers_not_found_in_paper"],1)
        self.assertEqual(info["saved_paper_quotes"],0)

    def test_same_quote_collision_and_late_capture_detected(self):
        x=offer()
        late={**x,"captured_at":TIP}
        info=audit({"records":[x,x,late]},board(),{"games":[]},{},
            now=datetime(2026,11,8,0,30,tzinfo=timezone.utc))
        self.assertIn("DUPLICATE_QUOTE_IDENTITY",info["paper_invariant_errors"])
        self.assertIn("LATE_CAPTURE",info["paper_invariant_errors"])

    def test_in_game_stat_checkpoint_preserves_actual_and_pra(self):
        r=capture(AT,scoreboard(),{"401909900":summary()})
        self.assertEqual(len(r["games"]),1)
        stats=r["games"][0]["player_rows"][0]
        self.assertEqual((stats["PTS"],stats["REB"],stats["AST"],stats["PRA"]),(14,6,7,27))
        self.assertTrue(r["no_betting_odds_or_model_predictions_modified"])
        with tempfile.TemporaryDirectory() as t:
            path=save(r,t)
            self.assertIsNotNone(path)
            saved=json.loads(gzip.decompress(path.read_bytes()))
            self.assertEqual(saved["games"],r["games"])
            self.assertEqual(save(r,t),path)

    def test_wrong_game_or_missing_stats_not_saved(self):
        invalid=capture(AT,scoreboard(),{"401909900":summary(False)})
        self.assertEqual(invalid["games"],[])
        self.assertEqual(invalid["errors"][0]["reason"],"MATCHUP_MISMATCH")
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(save(invalid,t))
        bad=summary()
        bad["boxscore"]["players"][0]["statistics"][0]["athletes"][0]["stats"][1]="—"
        self.assertEqual(players(bad),[])

    def test_no_live_game_writes_no_fake_stats(self):
        start=scoreboard()
        start["events"][0]["status"]["type"]["state"]="pre"
        r=capture(AT,start,{})
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(save(r,t))
        self.assertEqual(r["games"],[])

if __name__=="__main__":unittest.main()

import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from iphone_bot.assist_v2_shadow_capture import capture,summary,grade,verified_completed_games

class ShadowCaptureTests(unittest.TestCase):
    def test_reject_stale_board(self):
        board={"status":"EXPERIMENTAL_NON_CALIBRATED","verified_current_matchups":True,
               "generated_at":"2026-11-01T12:00:00+00:00","comparisons":[]}
        with self.assertRaises(ValueError):
            capture(board,[],[],now="2026-11-02T12:00:00+00:00")

    def test_preserve_existing(self):
        board={"status":"EXPERIMENTAL_NON_CALIBRATED","verified_current_matchups":True,
               "generated_at":"2026-11-07T12:00:00+00:00","comparisons":[]}
        old=[{"event_start":"2026-11-06T20:00:00+00:00","player_id":"1","team":"BOS","bookmaker":"x","line":3.5}]
        self.assertEqual(capture(board,[],old,now="2026-11-07T12:01:00+00:00"),old)

    def test_paired_prospective_summary_deduplicates_bookmakers(self):
        row={"event_start":"2026-11-07T20:00:00+00:00",
             "captured_at":"2026-11-07T18:00:00+00:00",
             "player_id":"1","team":"BOS","market":"AST","line":5.5,
             "status":"SETTLED","result":"WIN","actual":7,
             "baseline_projection":4.8,"v2_projection":6.2}
        r=summary([row,{**row,"bookmaker":"second"}])
        self.assertEqual(r["captured"],2)
        self.assertEqual(r["independent_settled_markets"],1)
        self.assertEqual(r["wins"],1)
        self.assertEqual(r["baseline_losses"],1)
        self.assertEqual(r["hit_rate"],1.)
        self.assertEqual(r["baseline_hit_rate"],0.)

    def test_shadow_reuses_completed_csv_and_verified_cbs_when_direct_espn_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ("data/nba/current/current_games.json",
                         "data/nba/current/cbs_final_boxscores.json"):
                path=root/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps([{"id":"1","player":"Test Player",
                   "date":"2026-11-07","team":"BOS","opponent":"MIA",
                   "MIN":32,"PTS":14,"REB":6,"AST":7}] if
                   name.endswith("current_games.json") else []))
            source=verified_completed_games(root)
            assert len(source)==1
            row={"event_start":"2026-11-07T21:00:00+00:00",
                 "captured_at":"2026-11-07T18:00:00+00:00",
                 "player_id":"1","player":"Test Player","team":"BOS",
                 "game":"Boston Celtics @ Miami Heat","market":"AST",
                 "line":5.5,"bookmaker":"test-book","american_odds":-110,
                 "side":"OVER","status":"PENDING"}
            result=grade([row],source,now="2026-11-08T03:00:00+00:00")
            self.assertEqual(result[0]["status"],"SETTLED")
            self.assertEqual(result[0]["actual"],7)
            self.assertEqual(result[0]["settlement_source"],"HISTORICAL_CSV_COMPLETED_GAME")

    def test_paired_scoring_excludes_baseline_no_lean_and_duplicate_books(self):
        common={"event_start":"2026-11-07T20:00:00+00:00",
                "captured_at":"2026-11-07T18:00:00+00:00",
                "player_id":"1","team":"BOS","market":"AST","line":5.5,
                "status":"SETTLED","result":"WIN","actual":7,
                "baseline_projection":4.8,"v2_projection":6.2}
        no_lean={**common,"player_id":"2","baseline_projection":5.5}
        a=summary([common,{**common,"bookmaker":"other"},no_lean])["paired_comparison"]
        self.assertEqual(a["paired_direction_markets"],1)
        self.assertEqual(a["paired_v2_wins"],1)
        self.assertEqual(a["paired_baseline_wins"],0)
        self.assertEqual(a["v2_only_correct"],1)
        self.assertEqual(a["distinct_game_dates"],1)
        self.assertFalse(a["promotion_eligible"])
        self.assertEqual(summary([])["paired_comparison"]["paired_v2_hit_rate"],None)

    def test_empty_grade_and_summary_are_safe(self):
        self.assertEqual(grade([],[],now="2026-11-07T20:00:00+00:00"),[])
        self.assertIsNone(summary([])["hit_rate"])
        self.assertEqual(summary([])["pending"],0)

    def test_capture_and_verified_final_grade_without_future_data(self):
        board={"status":"EXPERIMENTAL_NON_CALIBRATED","verified_current_matchups":True,
               "generated_at":"2026-11-07T18:00:00+00:00",
               "comparisons":[{"stat":"AST","start":"2026-11-07T21:00:00+00:00",
                               "player_id":"1","player":"Test Player","team":"BOS",
                               "game":"Boston Celtics @ Miami Heat","combined_projection":5.3,
                               "book_quotes":[{"name":"test-book","line":4.5,
                                               "over":-110,"under":-110}]}]}
        prediction={"status":"RESEARCH_FORECAST","projection":6.2,
                    "over_probability":0.68,"push_probability":0.,
                    "latest_prior_date":"2026-11-06","simulations":20000}
        with (patch("iphone_bot.assist_v2_shadow_capture.histories",return_value={}),
              patch("iphone_bot.assist_v2_shadow_capture.opportunity",return_value={"expected_minutes":30}),
              patch("iphone_bot.assist_v2_shadow_capture.forecast",return_value=prediction)):
            rows=capture(board,[],[],now="2026-11-07T18:10:00+00:00")
            repeated=capture(board,[],rows,now="2026-11-07T18:11:00+00:00")
        self.assertEqual(len(rows),1)
        self.assertEqual(len(repeated),1)
        self.assertEqual(rows[0]["side"],"OVER")
        self.assertFalse(rows[0]["production_applied"])
        final={"player":"Test Player","date":"2026-11-07","team":"BOS","opponent":"MIA",
               "source":"ESPN_FINAL","final_confirmed":True,"MIN":31,
               "PTS":18,"REB":4,"AST":7}
        graded=grade(rows,[final],now="2026-11-08T01:00:00+00:00")
        self.assertEqual(graded[0]["status"],"SETTLED")
        self.assertEqual(graded[0]["result"],"WIN")
        self.assertEqual(graded[0]["actual"],7)
        self.assertEqual(summary(graded)["independent_settled_markets"],1)

if __name__=="__main__":
    unittest.main()

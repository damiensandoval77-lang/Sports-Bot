import copy
import unittest
from research.join_matchup_features import assemble

FROZEN="2026-11-11T21:00:00Z"
START="2026-11-12T00:00:00Z"

def sources():
    evidence={"status":"SOURCE_LINKED_PREGAME_RESEARCH_ONLY",
        "captured_at":"2026-11-11T20:00:00Z",
        "production_hit_estimate_eligible":False,
        "future_games":[{"game_id":"game1","start":START,
          "home":"NYK","away":"BOS"}],
        "research_players":[{"game_id":"game1","player_id":"1","team":"BOS",
          "opponent":"NYK","start":START,"injury_status":"UNKNOWN_NOT_LISTED",
          "observed_minutes_last3":28,
          "minutes_source_published_at":"2026-11-11T19:00:00Z",
          "injury_report_issued_at":None}]}
    minutes={"prospective":{"status":"RESEARCH_MINUTES_ONLY",
      "captured_at":"2026-11-11T20:00:00Z",
      "production_approved":False,
      "predictions":[{"game_id":"game1","player_id":"1","team":"BOS",
        "opponent":"NYK","start":START,"captured_at":"2026-11-11T20:00:00Z",
        "source_published_at":"2026-11-11T19:00:00Z",
        "predicted_minutes_research":29,"model_id":"research-minutes"}]}}
    defense={"status":"POSITIONAL_BOX_SCORE_RESEARCH_ONLY",
      "captured_at":"2026-11-11T20:05:00Z",
      "production_hit_estimate_eligible":False,
      "future_games":[{"game_id":"game1","start":START,
        "player_positional_context":[{"player_id":"1","team":"BOS","opponent":"NYK",
          "listed_position":"PG","defense_games":5,
          "source_observed_at":"2026-11-11T19:00:00Z",
          "status":"THIRD_PARTY_LISTED_POSITION_ALLOWANCE_RESEARCH",
          "league_listed_position_baseline":{"PTS":10,"REB":5,"AST":4,"PRA":19},
          "defense_last5_per_listed_player":{"PTS":12,"REB":6,"AST":5,"PRA":23}}]}]}
    return evidence,minutes,defense

class JoinTests(unittest.TestCase):
    def test_exact_matchup_join_and_no_hit_probability(self):
        out=assemble(*sources(),captured_at=FROZEN)
        self.assertEqual(out["record_count"],1)
        self.assertEqual(out["players_with_both_position_and_minutes"],1)
        r=out["player_records"][0]
        self.assertEqual(r["listed_position"],"PG")
        self.assertEqual(r["research_minutes_forecast"],29)
        self.assertEqual(r["opponent_position_allowance_ratio_by_stat_research"]["PTS"],1.2)
        self.assertFalse(r["opponent_aware_hit_estimate_ready"])
        self.assertEqual(out["probabilities_generated"],0)

    def test_wrong_opponent_never_joins(self):
        e,m,p=sources()
        p["future_games"][0]["player_positional_context"][0]["opponent"]="TOR"
        out=assemble(e,m,p,captured_at=FROZEN)
        self.assertEqual(out["players_with_both_position_and_minutes"],0)

    def test_source_published_after_join_rejected(self):
        e,m,p=sources()
        p["future_games"][0]["player_positional_context"][0]["source_observed_at"]="2026-11-11T22:00:00Z"
        with self.assertRaises(ValueError):assemble(e,m,p,captured_at=FROZEN)

    def test_wrong_source_version_rejected(self):
        e,m,p=sources()
        m["prospective"]["predictions"][0]["source_published_at"]="2026-11-11T18:00:00Z"
        with self.assertRaises(ValueError):assemble(e,m,p,captured_at=FROZEN)

    def test_duplicate_identity_fails_closed(self):
        e,m,p=sources()
        m["prospective"]["predictions"].append(copy.deepcopy(m["prospective"]["predictions"][0]))
        with self.assertRaises(ValueError):assemble(e,m,p,captured_at=FROZEN)

    def test_started_game_excluded(self):
        out=assemble(*sources(),captured_at="2026-11-12T00:01:00Z")
        self.assertEqual(out["record_count"],0)

    def test_missing_minutes_never_fabricated(self):
        e,m,p=sources()
        m["prospective"]["predictions"]=[]
        out=assemble(e,m,p,captured_at=FROZEN)
        self.assertIsNone(out["player_records"][0]["research_minutes_forecast"])

    def test_missing_position_never_fabricated(self):
        e,m,p=sources()
        p["future_games"][0]["player_positional_context"]=[]
        out=assemble(e,m,p,captured_at=FROZEN)
        self.assertIsNone(out["player_records"][0]["opponent_position_allowance_ratio_by_stat_research"])

    def test_reject_invalid_position_reference(self):
        e,m,p=sources()
        p["future_games"][0]["player_positional_context"][0]["league_listed_position_baseline"]["PTS"]=0
        with self.assertRaises(ValueError):assemble(e,m,p,captured_at=FROZEN)

    def test_reject_unexpected_production_promotion(self):
        e,m,p=sources();m["prospective"]["production_approved"]=True
        with self.assertRaises(ValueError):assemble(e,m,p,captured_at=FROZEN)

if __name__=="__main__":unittest.main()

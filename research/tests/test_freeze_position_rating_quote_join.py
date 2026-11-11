import copy
import unittest
from research.freeze_position_rating_quote_join import assemble

FROZEN="2026-11-11T19:00:00Z"
SOURCE_TIME="2026-11-11T18:00:00Z"
NEXT="2026-11-12T01:00:00Z"
AFTER="2026-11-11T20:00:00Z"

def sources():
    quote={"status":"LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED",
        "predictions":[{"player_id":"201939","player":"Test Guard","team":"GSW",
        "opponent":"HOU","stat":"PTS","start":NEXT,
        "captured_at":FROZEN,"line":25.5,"projection":28.3,
        "pickem_tier":"standard","standard_line_two_sided_verified":True,
        "estimated_hit_chance":{"modeled_direction":"More"}}]}
    joined={"status":"SOURCED_MATCHUP_CONTEXT_RESEARCH_NOT_LIVE",
      "captured_at":SOURCE_TIME,
      "player_records":[{
        "player_id":"201939","team":"GSW","opponent":"HOU","start":NEXT,
        "captured_at":SOURCE_TIME,"listed_position":"PG",
        "opponent_defense_sample_games":7,
        "opponent_position_allowance_ratio_by_stat_research":{"PTS":1.08},
        "research_minutes_forecast":35,"observed_minutes_last3":34,
        "player_injury_status":"Available",
        "asof_source_times":{"position_source":SOURCE_TIME,
              "player_form":SOURCE_TIME,"minutes_snapshot":SOURCE_TIME}}]}
    rating={"status":"SOURCED_ESTIMATED_DEF_RATING_RESEARCH",
       "captured_at":SOURCE_TIME,"team_count":30,
       "teams":{"HOU":{"team":"HOU","defensive_rating":113,
         "league_defensive_rating":115,
         "metric":"ESTIMATED_POINTS_ALLOWED_PER_100_POSSESSIONS",
         "source":"https://example.org/verified-rating","observed_at":SOURCE_TIME}}}
    return quote,joined,rating

class AsofQuoteTests(unittest.TestCase):
    def test_genuine_pretip_source_joins_with_no_hit_probability(self):
        result=assemble(*sources(),captured_at=AFTER)
        self.assertEqual(result["qualified_experimental_projections"],1)
        item=result["results"][0]
        self.assertEqual(item["original_line"],25.5)
        self.assertFalse(item["production_approved"])
        self.assertIsNone(item["hit_probability"])
        self.assertTrue(item["source_frozen_before_quote"])
    def test_rating_published_after_pick_cannot_be_retrofit(self):
        q,j,r=sources()
        r["captured_at"]=AFTER
        r["teams"]["HOU"]["observed_at"]=AFTER
        result=assemble(q,j,r,captured_at="2026-11-11T21:00:00Z")
        self.assertEqual(result["qualified_experimental_projections"],0)
        self.assertEqual(result["exclusions"]["source_not_available_when_pick_frozen"],1)
    def test_context_published_after_pick_cannot_be_retrofit(self):
        q,j,r=sources();j["captured_at"]=AFTER
        result=assemble(q,j,r,captured_at="2026-11-11T21:00:00Z")
        self.assertEqual(result["qualified_experimental_projections"],0)
    def test_original_standard_line_unchanged(self):
        q,j,r=sources();qcopy=copy.deepcopy(q)
        assemble(q,j,r,captured_at=AFTER)
        self.assertEqual(q,qcopy)
    def test_promotional_line_rejected(self):
        q,j,r=sources();q["predictions"][0]["pickem_tier"]="demon"
        self.assertEqual(assemble(q,j,r,captured_at=AFTER)["qualified_experimental_projections"],0)
    def test_missing_opponent_position_rejected(self):
        q,j,r=sources();j["player_records"][0]["listed_position"]=None
        self.assertEqual(assemble(q,j,r,captured_at=AFTER)["qualified_experimental_projections"],0)
    def test_missing_def_rating_rejected(self):
        q,j,r=sources();r["teams"]["HOU"]["metric"]="PPG_ALLOWED"
        self.assertEqual(assemble(q,j,r,captured_at=AFTER)["qualified_experimental_projections"],0)
    def test_absent_minutes_rejected(self):
        q,j,r=sources();j["player_records"][0]["research_minutes_forecast"]=None
        self.assertEqual(assemble(q,j,r,captured_at=AFTER)["qualified_experimental_projections"],0)
    def test_wrong_opponent_does_not_join(self):
        q,j,r=sources();j["player_records"][0]["opponent"]="BOS"
        self.assertEqual(assemble(q,j,r,captured_at=AFTER)["qualified_experimental_projections"],0)
    def test_future_source_timestamp_rejected(self):
        q,j,r=sources();r["captured_at"]="2026-11-11T22:00:00Z"
        with self.assertRaises(ValueError):assemble(q,j,r,captured_at=AFTER)
    def test_current_or_started_game_not_recomputed(self):
        q,j,r=sources()
        self.assertEqual(assemble(q,j,r,captured_at="2026-11-12T02:00:00Z")["qualified_experimental_projections"],0)

if __name__=="__main__":unittest.main()

import copy
import unittest
from research.publish_matchup_shadow_guard import choose,validate

def feed(ts="2026-11-11T20:00:00Z"):
    r={"player_id":"1","team":"BOS","opponent":"NYK","stat":"PTS",
       "start":"2026-11-12T00:00:00Z","captured_at":"2026-11-11T19:00:00Z",
       "line":21.5,"original_side":"MORE",
       "estimated_hit_chance":{
          "method":"POSITION_V_POSITION_DEF_RATING_RESEARCH_ANALYTIC_V1",
          "calibrated":False,"research_only":True,"verified_betting_edge":False,
          "opponent_aware_inputs_sourced":True,"opponent_adjustment_validated":False,
          "modeled_selected_probability":.61}}
    return {"status":"POSITION_MATCHUP_RESEARCH_ONLY_PROBABILITY",
        "captured_at":ts,"eligible_opponent_conditioned_estimates":1,
        "production_approved":False,"published_to_cards":False,
        "calibrated":False,"records":[r]}

class PublisherTests(unittest.TestCase):
    def test_research_feed_validates_but_cannot_claim_certified_probability(self):
        f=feed();x,changed=choose(f)
        self.assertTrue(changed)
        self.assertEqual(x["presentation_policy"],"EXPERIMENTAL_MATCHUP_PREVIEW_NOT_CERTIFIED_HIT_EST")
        self.assertFalse(x["production_approved"])
    def test_later_arrival_does_not_overwrite_newer_snapshot(self):
        recent=feed("2026-11-11T21:00:00Z")
        old=feed("2026-11-11T20:00:00Z")
        chosen,changed=choose(old,recent)
        self.assertFalse(changed)
        self.assertEqual(chosen["captured_at"],recent["captured_at"])
    def test_empty_or_unverified_incoming_rejected(self):
        x=feed();x["records"]=[]
        with self.assertRaises(ValueError):validate(x)
        x=feed();x["estimated_hit_chance"]=None
        x["records"][0]["estimated_hit_chance"]["research_only"]=False
        with self.assertRaises(ValueError):validate(x)
    def test_posttip_quote_rejected(self):
        x=feed();x["records"][0]["captured_at"]=x["records"][0]["start"]
        with self.assertRaises(ValueError):validate(x)
    def test_unknown_model_does_not_get_displayed(self):
        x=feed();x["records"][0]["estimated_hit_chance"]["method"]="HISTORICAL_OVERS"
        with self.assertRaises(ValueError):validate(x)
    def test_duplicate_market_rejected(self):
        x=feed();x["records"].append(copy.deepcopy(x["records"][0]))
        x["eligible_opponent_conditioned_estimates"]=2
        with self.assertRaises(ValueError):validate(x)
if __name__=="__main__":unittest.main()

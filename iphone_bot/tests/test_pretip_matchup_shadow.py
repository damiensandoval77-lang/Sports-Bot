import unittest
import numpy as np
from research.pretip_matchup_shadow import analyze

FREEZE="2026-11-11T20:00:00Z"
START="2026-11-12T02:30:00Z"
NOW="2026-11-11T20:10:00Z"
def fixtures():
    p={"player_id":"201939","player":"Example","team":"GSW","opponent":"HOU",
        "stat":"PTS","line":27.5,"projection":29.8,"start":START,
        "captured_at":FREEZE,"estimated_hit_chance":{"modeled_direction":"More"}}
    quote={"status":"LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED","predictions":[p]}
    match={"captured_at":NOW,"input_quotes":1,"exclusions":{},
          "results":[{"player_id":p["player_id"],"player":p["player"],
          "team":"GSW","opponent":"HOU","stat":"PTS","original_line":27.5,
          "original_projection":29.8,"experimental_matchup_projection":32.1,
          "position":"PG","start":START,"pick_captured_at":FREEZE,
          "source_provenance":{"position_observed_at":"2026-11-11T19:00:00Z"}}]}
    return quote,match

class MatchupShadowTests(unittest.TestCase):
    def test_distribution_centers_on_opponent_adjusted_projection(self):
        q,j=fixtures()
        residuals=np.array([[float((i%9)-4),0,0] for i in range(1200)])
        a=analyze(q,j,residuals,captured_at=NOW,model_id="research")
        self.assertEqual(a["eligible_opponent_conditioned_estimates"],1)
        x=a["records"][0]
        self.assertGreater(x["estimated_hit_chance"]["modeled_selected_probability"],.5)
        self.assertEqual(x["matchup_projection"],32.1)
        self.assertFalse(a["published_to_cards"])
        self.assertFalse(a["calibrated"])
    def test_same_quote_with_weaker_opponent_adjustment_reduces_over_chance(self):
        q,j=fixtures()
        residuals=np.array([[float((i%9)-4),0,0] for i in range(1200)])
        a=analyze(q,j,residuals,captured_at=NOW,model_id="research")
        j["results"][0]["experimental_matchup_projection"]=26.1
        b=analyze(q,j,residuals,captured_at=NOW,model_id="research")
        self.assertGreater(a["records"][0]["estimated_hit_chance"]["modeled_selected_probability"],
                           b["records"][0]["estimated_hit_chance"]["modeled_selected_probability"])
    def test_exact_match_of_frozen_price_and_player_required(self):
        q,j=fixtures();j["results"][0]["original_line"]=29.5
        with self.assertRaises(ValueError):
            analyze(q,j,np.zeros((1001,3)),captured_at=NOW,model_id="research")
    def test_insufficient_residuals_fails_closed(self):
        q,j=fixtures()
        with self.assertRaises(ValueError):
            analyze(q,j,np.zeros((40,3)),captured_at=NOW,model_id="research")
    def test_pra_uses_correlated_three_stat_error_sum(self):
        q,j=fixtures()
        q["predictions"][0]["stat"]="PRA"
        j["results"][0]["stat"]="PRA"
        residuals=np.tile(np.array([[1.,2.,3.],[-1.,-2.,-3.]]),(600,1))
        r=analyze(q,j,residuals,captured_at=NOW,model_id="research")
        self.assertEqual(r["records"][0]["estimated_hit_chance"]["reference_validation_games"],1200)
    def test_never_convert_to_historical_line_hit_rate(self):
        q,j=fixtures()
        q["predictions"][0]["estimated_hit_chance"]["modeled_selected_probability"]=.01
        a=analyze(q,j,np.zeros((1200,3)),captured_at=NOW,model_id="research")
        self.assertNotEqual(a["records"][0]["estimated_hit_chance"]["modeled_selected_probability"],.01)
if __name__=="__main__":unittest.main()

import unittest
from iphone_bot.grade_quality_scorecard import build

def data():
    return {"generated_at":"2026-11-08T08:56:57Z",
      "performance":{"models":{"combined":{"direction_eligible":5,
        "direction_wins":2,"direction_losses":3,"direction_hit_rate":.4,
        "paper_roi_per_priced_unit":-.2}},
       "by_stat":{"PTS":{"combined":{"direction_eligible":2,
          "direction_wins":1,"direction_losses":1,"direction_hit_rate":.5}},
         "REB":{"combined":{"direction_eligible":1,"direction_wins":0,
         "direction_losses":1,"direction_hit_rate":0}},
         "AST":{"combined":{"direction_eligible":1,"direction_wins":1,
         "direction_losses":0,"direction_hit_rate":1}},
         "PRA":{"combined":{"direction_eligible":1,"direction_wins":0,
         "direction_losses":1,"direction_hit_rate":0}}}},
      "accuracy_feedback":{"overall":{"overall":{"distinct_game_dates":2}}},
      "probability_audit":{"overall":{"sample_size":5,"average_estimated_probability":.7,
          "observed_hit_rate":.4,"calibration_gap":-.3},
          "sufficient_overall_sample":False},
      "selective_challenger":{"by_stat":{"PTS":{"wins":1,"losses":0},
        "REB":{"wins":0,"losses":1}}}}

class ScorecardTests(unittest.TestCase):
    def test_conservatively_exposes_real_grade_and_overconfidence(self):
        r=build(data())
        self.assertEqual(r["all_model_directions"]["n"],5)
        self.assertEqual(r["independent_game_dates"],2)
        self.assertEqual(r["prospective_selective_research"]["n"],2)
        self.assertFalse(r["prospective_selective_research"]["validated"])
        self.assertFalse(r["main_board_probability_usable"])
        self.assertFalse(r["main_board_ev_usable"])
        self.assertEqual(r["by_market"][1]["hit_rate"],0)
        self.assertEqual(r["original_probability_audit"]["calibration_gap"],-.3)
    def test_never_silently_accept_count_mismatch(self):
        x=data();x["performance"]["models"]["combined"]["direction_eligible"]=6
        with self.assertRaises(AssertionError):build(x)

if __name__=="__main__":unittest.main()

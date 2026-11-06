import unittest
from iphone_bot.combined_projection import combine_projections,METHOD
from iphone_bot.paper_pick_pipeline import snapshot

class CombinedProjectionTest(unittest.TestCase):
    def test_two_model_median_is_midpoint(self):
        combined=combine_projections(25.8,22.2)
        self.assertAlmostEqual(combined["projection"],24.0)
        self.assertEqual(combined["model_count"],2)
        self.assertEqual(combined["method"],METHOD)
        self.assertFalse(combined["ensemble_validated"])

    def test_missing_shadow_uses_original(self):
        value=combine_projections(21.5)
        self.assertEqual(value["projection"],21.5)
        self.assertEqual(value["model_count"],1)
        self.assertEqual(value["method"],"ORIGINAL_AI_FALLBACK")

    def test_paper_pick_freezes_combined_direction(self):
        row={"player":"Test Player","player_id":"444","team":"BOS","stat":"PTS",
             "game":"Boston Celtics @ Miami Heat","start":"2026-11-13T00:30:00Z",
             "projection":28.0,"combined_projection":23.0,
             "combined_method":METHOD,"combined_model_count":2,
             "book_quotes":[{"name":"Book","line":25.5,"over":-110,"under":-110}]}
        stored=snapshot([row],"2026-11-12T19:00:00Z")
        self.assertEqual(stored[0]["side"],"UNDER")
        self.assertEqual(stored[0]["combined_projection"],23.0)
        self.assertEqual(stored[0]["original_projection"],28.0)
        self.assertEqual(stored[0]["model"],"TWO_MODEL_MEDIAN_RESEARCH")

if __name__=="__main__":unittest.main()

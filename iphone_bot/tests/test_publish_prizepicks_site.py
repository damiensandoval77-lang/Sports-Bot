import unittest
from iphone_bot.publish_prizepicks_site import summarize

def offer():
    return {"id":"pp_100","player":"Sample Player","team":"BOS",
      "game":"Boston Celtics @ Miami Heat","stat":"PTS","line":24.5,
      "starts_at":"2026-12-20T01:00:00Z","observed_at":"2026-12-19T21:00:00Z",
      "more_tier":"standard","less_tier":"standard","is_demo":False,
      "source":"independent_prizepicksapi_com",
      "unwanted_private_extra":"not_for_mobile"}

class PrizePicksSiteTests(unittest.TestCase):
    def test_slim_preserves_real_line_not_unneeded_fields(self):
        source={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
          "generated_at":"2026-12-19T21:00:00Z","provider_status":"fresh",
          "complete_provider_board":True,
          "board_offers":[offer()],"offers":[]}
        schedule={"coverage_complete":False,"games":[
            {"game":"Boston Celtics @ Miami Heat","start":"2026-12-20T01:00:00Z"},
            {"game":"New York Knicks @ Brooklyn Nets","start":"2026-12-20T01:00:00Z"}]}
        site,health=summarize(source,schedule)
        self.assertEqual(site["independent_board_count"],1)
        self.assertNotIn("unwanted_private_extra",site["board_offers"][0])
        self.assertEqual(site["board_offers"][0]["line"],24.5)
        self.assertEqual(health["markets_by_game"]["Boston Celtics @ Miami Heat"],1)
        self.assertFalse(health["real_american_odds_provided"])
        self.assertFalse(health["schedule_is_independently_complete"])

    def test_reject_demo_rows_and_missing_available_sides(self):
        bad=dict(offer(),is_demo=True)
        invalid=dict(offer(),more_tier=None,less_tier=None)
        source={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
          "board_offers":[bad,invalid],"offers":[]}
        site,_=summarize(source,{"games":[]})
        self.assertEqual(site["board_offers"],[])
        self.assertEqual(site["independent_board_count"],0)

if __name__=="__main__":unittest.main()

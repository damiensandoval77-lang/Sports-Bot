import unittest
from unittest.mock import patch
from iphone_bot.probe_tracking_provider import evaluate_schema,probe

class TrackingProviderProbeTests(unittest.TestCase):
    def test_season_tracking_is_never_mislabeled_as_dated_game_samples(self):
        payload={"data":{"items":[
            {"player_id":"10","games_played":10,"minutes_per_game":30,
             "passing":{"potential_assists":11,"assists":6},
             "rebounding":{"rebound_chances":14,"rebounds":7}},
            {"player_id":"11","passing":None,"rebounding":None}]}}
        result=evaluate_schema(payload)
        self.assertTrue(result["has_both_opportunity_fields"])
        self.assertFalse(result["has_dated_player_game_rows"])
        self.assertFalse(result["qualified_for_pregame_gamelevel_import"])
        self.assertEqual(result["players_with_both_fields"],1)
        self.assertEqual(result["tracked_players"],2)
    def test_missing_token_does_not_make_network_call(self):
        with patch("iphone_bot.probe_tracking_provider.urllib.request.urlopen") as network:
            result=probe(token="")
        self.assertEqual(result["status"],"NOT_CONFIGURED_NEEDS_PROVIDER_TOKEN")
        self.assertFalse(result["gamelevel_tracking_connected"])
        network.assert_not_called()
    def test_empty_and_wrong_schema_rejected(self):
        self.assertFalse(evaluate_schema({"data":{"items":[]}})["has_both_opportunity_fields"])
        self.assertEqual(evaluate_schema({"data":{}})["schema"],"NO_EXPECTED_ITEMS")
    def test_game_date_fields_still_cannot_claim_import_ready(self):
        row={"player_id":"10","game_id":"0022600001","game_date":"2026-11-01",
             "minutes":30,"passing":{"potential_assists":11},
             "rebounding":{"rebound_chances":14}}
        result=evaluate_schema({"data":{"items":[row]}})
        self.assertTrue(result["has_dated_player_game_rows"])
        self.assertFalse(result["qualified_for_pregame_gamelevel_import"])
        self.assertFalse(result["date_provenance_verified"])

if __name__=="__main__":unittest.main()

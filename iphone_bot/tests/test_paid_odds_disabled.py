"""Existing credentials must never implicitly authorize billable polling."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from iphone_bot import fetch_props, fetch_game_moneylines, fetch_odds_scores

class PaidPollingPolicyTests(unittest.TestCase):
    def test_all_paid_collectors_default_to_no_network_and_preserve_data(self):
        for module in (fetch_props, fetch_game_moneylines, fetch_odds_scores):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as temp:
                out=Path(temp)/"observed.json"
                out.write_text('{"original":"immutable"}')
                status=Path(temp)/"status.json"
                with patch.dict(os.environ,{"ODDS_API_KEY":"dummy-existing-credential","SPORTS_BOT_ENABLE_PAID_ODDS":"0"}), \
                     patch.object(module,"OUT",out),patch.object(module,"STATUS",status), \
                     patch("urllib.request.urlopen",side_effect=AssertionError("Network forbidden")) as network:
                    module.main()
                network.assert_not_called()
                self.assertEqual(out.read_text(),'{"original":"immutable"}')
                self.assertIn('PAID_ODDS_POLLING_DISABLED',status.read_text())

    def test_missing_opt_in_is_also_disabled(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{},clear=True), \
             patch.object(fetch_props,"STATUS",Path(temp)/"status.json"), \
             patch.object(fetch_props,"request") as request:
            fetch_props.main()
            request.assert_not_called()

if __name__=="__main__":unittest.main()

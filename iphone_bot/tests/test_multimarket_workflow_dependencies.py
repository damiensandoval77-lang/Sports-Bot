"""Changes to shared current-game history must regenerate the actual live board."""
import unittest
from pathlib import Path

class MultimarketWorkflowDependencies(unittest.TestCase):
    def test_shared_history_changes_trigger_both_pr_and_main(self):
        root = Path(__file__).resolve().parents[2]
        text = (root/'.github/workflows/nba-new-ai-all-markets.yml').read_text()
        pull = text.split('  pull_request:', 1)[1].split('  workflow_dispatch:', 1)[0]
        push = text.split('  push:', 1)[1].split('  schedule:', 1)[0]
        for trigger in (pull, push):
            self.assertIn("'iphone_bot/live_lagged_matchup_sidecar.py'", trigger)
            self.assertIn("'iphone_bot/tests/test_live_lagged_matchup_sidecar.py'", trigger)
            self.assertIn("'iphone_bot/tests/test_multimarket_workflow_dependencies.py'", trigger)
        self.assertIn("-p 'test_live_lagged_matchup_sidecar.py'", text)
        self.assertIn("-p 'test_multimarket_workflow_dependencies.py'", text)

if __name__ == '__main__':
    unittest.main()

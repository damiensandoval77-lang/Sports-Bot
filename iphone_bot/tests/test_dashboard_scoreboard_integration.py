"""Run current NBA/NFL browser scoreboard contracts, not retired root widgets."""
import subprocess
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
class DashboardScoreboardIntegrationTests(unittest.TestCase):
    def test_canonical_live_identity_freshness_and_fallback_contracts(self):
        result = subprocess.run(["node", "--test", "iphone_bot/tests/test_live_direct.cjs",
                                 "iphone_bot/tests/test_root_redirect.cjs"],
                                cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
if __name__ == "__main__":
    unittest.main()

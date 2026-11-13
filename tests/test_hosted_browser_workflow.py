"""Hosted release checks must finish and compare only deployed main."""
import unittest
from pathlib import Path
import yaml

class HostedBrowserWorkflowTests(unittest.TestCase):
    def test_hosted_verifier_is_not_run_against_unpublished_pr(self):
        workflow = yaml.safe_load(Path('.github/workflows/live-site-e2e.yml').read_text())
        triggers = workflow.get('on', workflow.get(True))
        self.assertNotIn('pull_request', triggers)
        self.assertEqual(triggers['push']['branches'], ['main'])
        self.assertIn('workflow_run', triggers)
        self.assertIn('schedule', triggers)

    def test_frequent_publications_do_not_cancel_active_browser_proof(self):
        workflow = yaml.safe_load(Path('.github/workflows/live-site-e2e.yml').read_text())
        self.assertIs(workflow['concurrency']['cancel-in-progress'], False)

if __name__ == '__main__':
    unittest.main()

import unittest
from pathlib import Path
import yaml

class IsolatedResearchWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.job=yaml.safe_load(Path('.github/workflows/nba-new-ai-all-markets.yml').read_text())['jobs']['short-history-research']
    def test_pr_runs_cannot_displace_production_recovery(self):
        workflow=yaml.safe_load(Path('.github/workflows/nba-new-ai-all-markets.yml').read_text())
        self.assertIn("github.event_name == 'pull_request'",workflow['concurrency']['group'])
        self.assertIn("github.event.pull_request.number",workflow['concurrency']['group'])
        self.assertIn("'production'",workflow['concurrency']['group'])
        self.assertIs(workflow['concurrency']['cancel-in-progress'],False)
    def test_durable_merge_repairs_trigger_actual_publication(self):
        text=Path('.github/workflows/nba-new-ai-all-markets.yml').read_text()
        push=text.split('  push:',1)[1].split('  schedule:',1)[0]
        self.assertIn("'iphone_bot/merge_new_ai_publishing.py'",push)
        self.assertIn("'iphone_bot/multimarket_forecast_ledger.py'",push)
    def test_runs_after_primary_even_on_failure(self):
        self.assertEqual(self.job['needs'],['multi-market'])
        self.assertIn('always()',self.job['if'])
    def test_source_failure_clears_and_only_separate_outputs_are_published(self):
        step=next(s for s in self.job['steps'] if s.get('name','').startswith('Publish only separate research'))
        self.assertIn("github.event_name != 'pull_request'",step['if'])
        self.assertIn('--blocked SOURCE_OR_TRAINING_FAILED',step['run'])
        self.assertIn('git fetch origin main',step['run'])
        self.assertIn('python -m iphone_bot.fetch_current_form',step['run'])
        self.assertIn('python -m iphone_bot.build_prizepicks_model_input',step['run'])
        adds=[x.strip() for x in step['run'].splitlines() if x.strip().startswith('git add')]
        self.assertEqual(adds,['git add docs/short_history_model.json','git add docs/short_history_model_validation.json'])
    def test_reproduction_is_pinned_and_no_paid_source_called(self):
        text='\n'.join(x.get('run','') for x in self.job['steps'])
        self.assertIn('scikit-learn==1.8.0',text)
        self.assertIn('numpy==2.3.5',text)
        self.assertIn('short_history_candidate --download',text)
        self.assertNotIn('fetch_prizepicks',text)
if __name__=='__main__':unittest.main()

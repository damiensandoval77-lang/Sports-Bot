import unittest
from datetime import datetime, timezone
from iphone_bot.quote_refresh_integrity import check

class QuoteRefreshIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,14,0,0,tzinfo=timezone.utc)
        self.source={'status':'LIVE_THIRD_PARTY_PRIZEPICKS_LINES','provider_status':'fresh','generated_at':'2026-11-13T23:57:00+00:00'}
        self.model={'source_provider_generated_at':'2026-11-13T23:05:00+00:00'}
    def test_new_quote_snapshot_requires_refresh(self):
        self.assertFalse(check(self.source,self.model,self.now)['safe'])
    def test_same_snapshot_passes(self):
        self.model['source_provider_generated_at']=self.source['generated_at']
        self.assertTrue(check(self.source,self.model,self.now)['safe'])
    def test_newer_model_does_not_regress(self):
        self.model['source_provider_generated_at']='2026-11-13T23:58:00+00:00'
        self.assertTrue(check(self.source,self.model,self.now)['safe'])
    def test_future_or_missing_provenance_fails(self):
        for value in [None,'bad','2026-11-14T00:01:00+00:00','2026-11-13T23:58:00']:
            self.model['source_provider_generated_at']=value
            self.assertFalse(check(self.source,self.model,self.now)['safe'])
    def test_unverified_feed_does_not_replace_valid_model(self):
        self.source['provider_status']='error'
        self.assertTrue(check(self.source,self.model,self.now)['safe'])

class QuoteWorkflowTests(unittest.TestCase):
    def test_quote_guard_and_capture_preservation_precede_publish(self):
        from pathlib import Path
        import yaml
        workflow=Path(__file__).resolve().parents[2]/'.github/workflows/nba-new-ai-all-markets.yml'
        d=yaml.safe_load(workflow.read_text())
        steps=[x for job in d['jobs'].values() for x in job.get('steps',[])]
        publish=next(x['run'] for x in steps if x.get('name','').startswith('Publish ONLY separate new AI'))
        self.assertLess(publish.index('quote_refresh_integrity'),publish.index('injury_refresh_integrity'))
        section=publish[publish.index('quote_refresh_integrity'):publish.index('# Rebuild against the latest official')]
        self.assertIn('"$quote_regen" -gt 3',section)
        self.assertLess(section.index('build_prizepicks_model_input'),section.index('live_multimarket_matchup.py'))
        self.assertLess(section.index('merge_new_ai_publishing'),section.index('cp docs/lagged_matchup_all_market_ledger.json'))
        self.assertIn('--incoming "$RUNNER_TEMP/new-ai-ledger.json"',section)
        self.assertIn('continue',section)

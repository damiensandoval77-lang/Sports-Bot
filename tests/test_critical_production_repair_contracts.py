"""Regression safeguards for production repair workflows and paid-source boundaries."""
import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/".github/workflows"

def load(name):
    return yaml.safe_load((WORK/name).read_text())

def step(name,step_name):
    data=load(name)
    for job in data["jobs"].values():
        for item in job.get("steps",[]):
            if item.get("name")==step_name:return item
    raise AssertionError(name+": step not found: "+step_name)

class CriticalProductionRepairContracts(unittest.TestCase):
    def test_write_capable_health_controllers_pin_external_actions(self):
        import re
        for name in ('pipeline-heartbeat.yml', 'production_readiness.yml'):
            for job in load(name)['jobs'].values():
                for item in job.get('steps', []):
                    action = item.get('uses', '')
                    if action and not action.startswith('./'):
                        self.assertRegex(action, r'^[^@]+@[0-9a-f]{40}$', name)

    def test_free_collector_never_networks_or_writes_in_pr(self):
        name="nba-prizepicks-full-slate.yml"
        data=load(name)
        self.assertIn("pull_request",data.get("on",data.get(True,{})))
        for title in ("Fetch free public standard NBA quotes (no paid fallback)",
                      "Archive original independent pick'em lines and tiers",
                      "Save real PrizePicks observations without modifying sportsbook odds"):
            self.assertIn("github.event_name != 'pull_request'",step(name,title)["if"])
        self.assertNotIn("if",step(name,"Test strict native quote provenance and existing publisher compatibility"))
        self.assertNotIn("PRIZEPICKS_API_KEY",(WORK/name).read_text())
        self.assertNotIn("python -u iphone_bot/fetch_prizepicks.py",(WORK/name).read_text())

    def test_paid_source_is_not_auto_dispatched_by_heartbeat(self):
        text=(ROOT/"iphone_bot/pipeline_heartbeat.py").read_text()
        self.assertIn("lines_coverage",text)
        self.assertIn("next_slate",text)
        self.assertIn("capture_integrity",text)
        self.assertIn("prizepicks_grade_backlog",text)
        self.assertIn("ai_grade_backlog",text)
        self.assertNotIn('"lines_coverage":"nba-prizepicks-full-slate.yml"',text)
        self.assertIn("recovery_workflow=None",text)

    def test_quota_probe_requires_explicit_paid_authorization(self):
        from unittest.mock import patch
        from iphone_bot import check_prizepicks_live_access as probe
        with patch.object(probe.urllib.request, 'urlopen') as request:
            result=probe.check('fake-test-key')
        request.assert_not_called()
        self.assertEqual(result['status'], 'PAID_REQUEST_NOT_AUTHORIZED')
        self.assertEqual(result['credit_cost'], 0)
        data=load('nba-prizepicks-current-balance.yml')
        triggers=data.get('on',data.get(True,{}))
        self.assertEqual(set(triggers), {'workflow_dispatch'})
        self.assertFalse(triggers['workflow_dispatch']['inputs']['allow_paid_request']['default'])
        gate=data['jobs']['check']['if']
        self.assertIn("github.event_name == 'workflow_dispatch'", gate)
        self.assertIn('inputs.allow_paid_request == true', gate)

    def test_schema_probe_import_and_default_execution_make_no_request(self):
        from unittest.mock import patch
        import importlib
        with patch('urllib.request.urlopen') as request:
            module=importlib.import_module('iphone_bot.inspect_prizepicks_compact_schema')
            module.main([])
        request.assert_not_called()
        data=load('inspect-prizepicks-compact.yml')
        triggers=data.get('on',data.get(True,{}))
        self.assertEqual(set(triggers), {'workflow_dispatch'})
        self.assertFalse(triggers['workflow_dispatch']['inputs']['allow_paid_request']['default'])
        self.assertIn('inputs.allow_paid_request == true', data['jobs']['inspect']['if'])

    def test_failed_free_workflow_does_not_enforce_cooldown(self):
        text=(WORK/"production_readiness.yml").read_text()
        self.assertIn('.conclusion == "success"',text)
        self.assertIn('$paid == "true"',text)
        self.assertIn("nba-prizepicks-full-slate.yml",text)

    def test_new_market_snapshot_invalidates_old_successful_model(self):
        text=(WORK/"nba-prizepicks-site-publish.yml").read_text()
        self.assertIn("python -m iphone_bot.model_dispatch_recovery --source docs/prizepicks_model_input.json",text)
        from iphone_bot.model_dispatch_recovery import covering_runs
        import datetime as dt
        now=dt.datetime(2026,11,12,23,0,tzinfo=dt.timezone.utc)
        prior_success={"headBranch":"main","status":"completed","conclusion":"success",
                       "createdAt":"2026-11-12T22:40:00Z"}
        self.assertFalse(covering_runs([prior_success],"2026-11-12T22:50:00Z",now))
        self.assertNotIn("python -u iphone_bot/fetch_prizepicks.py",text)

    def test_legacy_pages_mode_is_verified_not_mutated(self):
        text=(WORK/"pages-controlled.yml").read_text()
        self.assertIn("scripts/verify_legacy_pages_release.py",text)
        self.assertIn("mode=$(gh api",text)
        self.assertNotIn("gh api -X PUT",text)
        self.assertIn("if: github.event_name != 'pull_request'",text)

    def test_pretip_only_recovery_guard(self):
        from iphone_bot.pipeline_heartbeat import evaluate
        import datetime as dt
        now=dt.datetime(2026,11,11,23,30,tzinfo=dt.timezone.utc)
        event=(now-dt.timedelta(hours=2)).isoformat()
        game="Boston Celtics @ Toronto Raptors"
        offer={"game":game,"starts_at":event,"more_tier":"standard","less_tier":"standard"}
        site={"nba_schedule.json":{"coverage_complete":True,
                                   "games":[{"game":game,"start":event,"date_eastern":"2026-11-11"}]},
              "prizepicks.json":{"generated_at":now.isoformat(),"board_offers":[offer]},
              "prizepicks_site.json":{"generated_at":now.isoformat(),"board_offers":[offer]}}
        report=evaluate(now,site)
        state=next(s for s in report["stages"] if s["stage"]=="picks_frozen")
        self.assertEqual(state["status"],"FAIL")
        self.assertIsNone(state["recovery_workflow"],"Past games cannot be backdated as new pretip picks")

if __name__=="__main__":unittest.main()

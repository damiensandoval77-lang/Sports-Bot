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
    def test_paid_collector_is_never_called_in_pr(self):
        name="nba-prizepicks-full-slate.yml"
        data=load(name)
        self.assertIn("pull_request",data.get("on",data.get(True,{})))
        for title in ("Fetch bounded, cursor-paged actual NBA PrizePicks board",
                      "Archive original independent pick'em lines and tiers",
                      "Save real PrizePicks observations without modifying sportsbook odds"):
            self.assertIn("github.event_name != 'pull_request'",step(name,title)["if"])
        self.assertEqual(step(name,"Test strict pregame event, team, market and source matching")["if"],
                         "github.event_name == 'pull_request'")

    def test_paid_source_is_not_auto_dispatched_by_heartbeat(self):
        text=(ROOT/"iphone_bot/pipeline_heartbeat.py").read_text()
        self.assertIn("lines_coverage",text)
        self.assertIn("next_slate",text)
        self.assertIn("capture_integrity",text)
        self.assertIn("prizepicks_grade_backlog",text)
        self.assertIn("ai_grade_backlog",text)
        self.assertNotIn('"lines_coverage":"nba-prizepicks-full-slate.yml"',text)
        self.assertIn("recovery_workflow=None",text)

    def test_failed_free_workflow_does_not_enforce_cooldown(self):
        text=(WORK/"production_readiness.yml").read_text()
        self.assertIn('.conclusion == "success"',text)
        self.assertIn('$paid == "true"',text)
        self.assertIn("nba-prizepicks-full-slate.yml",text)

    def test_new_market_snapshot_invalidates_old_successful_model(self):
        text=(WORK/"nba-prizepicks-site-publish.yml").read_text()
        self.assertIn("latest_source_epoch",text)
        self.assertIn('(.createdAt | fromdateiso8601) >= $source',text)
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

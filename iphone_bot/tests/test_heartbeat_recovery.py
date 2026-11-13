import datetime as dt
import json
import subprocess
import unittest
import os
import tempfile
from pathlib import Path
from iphone_bot.heartbeat_recovery import recover

NOW = dt.datetime(2026, 11, 13, 8, 0, tzinfo=dt.timezone.utc)
A = "independent_nba_player_boxscores.yml"
B = "independent_scoreboard_refresh.yml"


def report(*workflows):
    return {"stages": [{"status": "FAIL", "recovery_workflow": w} for w in workflows]}


class Recovery(unittest.TestCase):
    def test_actions_summary_renders_actual_status_and_recovery_after_failure(self):
        import yaml
        root = Path(__file__).resolve().parents[2]
        workflow = yaml.safe_load((root / ".github/workflows/pipeline-heartbeat.yml").read_text())
        steps = workflow["jobs"]["heartbeat"]["steps"]
        summary = next(s for s in steps if s.get("name") == "Publish source-grounded status in the Actions run summary")
        self.assertIn("always()", summary["if"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "pipeline_heartbeat.json").write_text(json.dumps({"stages": [{
                "status": "FAIL", "stage": "live_players", "detail": "Missing box", "evidence": {"missing": ["A @ B"]}}]}))
            (path / "heartbeat_recovery.json").write_text(json.dumps({"recoveries": [{
                "status": "FAILED", "workflow": A, "reason": "DISPATCH_FAILED"}]}))
            output = path / "summary.md"
            subprocess.run(["bash", "-e", "-c", summary["run"]], cwd=path,
                           env={**os.environ, "GITHUB_STEP_SUMMARY": str(output)}, check=True, capture_output=True)
            text = output.read_text()
            self.assertIn("**FAIL** live_players: Missing box", text)
            self.assertIn("A @ B", text)
            self.assertIn("Recovery **FAILED** " + A + ": DISPATCH_FAILED", text)
            self.assertNotIn("\\(.status)", text)

    def test_failed_dispatch_does_not_skip_later_stage(self):
        calls = []
        def command(args):
            calls.append(args)
            if args[:2] == ["run", "list"]:
                return "[]"
            if args[2] == A:
                raise RuntimeError("dispatch denied")
            return ""
        result = recover(report(A, B), now=NOW, command=command)
        self.assertEqual([x["status"] for x in result["recoveries"]], ["FAILED", "DISPATCHED"])
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertIn(["workflow", "run", B, "--ref", "main"], calls)

    def test_inventory_timeout_does_not_dispatch_blind_or_skip_other_stage(self):
        calls = []
        def command(args):
            calls.append(args)
            if args[:2] == ["run", "list"] and args[3] == A:
                raise subprocess.TimeoutExpired("gh", 45)
            return "[]" if args[0] == "run" else ""
        result = recover(report(A, B), now=NOW, command=command)
        self.assertEqual([x["status"] for x in result["recoveries"]], ["BLOCKED", "DISPATCHED"])
        self.assertNotIn(["workflow", "run", A, "--ref", "main"], calls)

    def test_paid_unknown_and_injected_workflows_never_execute(self):
        calls = []
        result = recover(report("nba-prizepicks-full-slate.yml", "unknown.yml", "a; echo unsafe"), now=NOW,
                         command=lambda args: calls.append(args))
        self.assertEqual(calls, [])
        self.assertTrue(all(x["status"] == "BLOCKED" for x in result["recoveries"]))

    def test_failed_runs_do_not_cool_down_and_duplicate_stage_dispatches_once(self):
        calls = []
        runs = [{"headBranch": "main", "status": "completed", "conclusion": "failure",
                 "createdAt": NOW.isoformat()}]
        def command(args):
            calls.append(args)
            return json.dumps(runs) if args[0] == "run" else ""
        result = recover(report(A, A), now=NOW, command=command)
        self.assertEqual(len(result["recoveries"]), 1)
        self.assertEqual(result["recoveries"][0]["status"], "DISPATCHED")
        self.assertEqual(len(calls), 2)

    def test_active_and_recent_success_main_runs_suppress_duplicate(self):
        for status, conclusion in [("queued", None), ("in_progress", None), ("completed", "success")]:
            with self.subTest(status=status):
                runs = [{"headBranch": "main", "status": status, "conclusion": conclusion,
                         "createdAt": (NOW-dt.timedelta(minutes=10)).isoformat()}]
                calls = []
                def command(args):
                    calls.append(args)
                    return json.dumps(runs)
                result = recover(report(A), now=NOW, command=command)
                self.assertEqual(result["recoveries"][0]["status"], "SKIPPED")
                self.assertEqual(len(calls), 1)

    def test_old_success_or_other_branch_does_not_hide_recovery(self):
        for branch, minutes in [("main", 31), ("repair", 1)]:
            runs = [{"headBranch": branch, "status": "completed", "conclusion": "success",
                     "createdAt": (NOW-dt.timedelta(minutes=minutes)).isoformat()}]
            result = recover(report(A), now=NOW, command=lambda args: json.dumps(runs) if args[0]=="run" else "")
            self.assertEqual(result["recoveries"][0]["status"], "DISPATCHED")

    def test_malformed_or_future_inventory_is_blocked_not_green(self):
        for raw in ["not json", "{}", '[null]', json.dumps([{"headBranch":"main", "status":"completed",
                "conclusion":"success", "createdAt":(NOW+dt.timedelta(hours=1)).isoformat()}])]:
            result = recover(report(A), now=NOW, command=lambda args: raw)
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual(result["recoveries"][0]["status"], "BLOCKED")

    def test_warning_and_pass_do_not_trigger_recovery(self):
        data = {"stages": [{"status": state, "recovery_workflow": A} for state in ["OK", "WARN"]]}
        self.assertEqual(recover(data, now=NOW, command=lambda args: self.fail("unexpected dispatch"))["recoveries"], [])


if __name__ == "__main__":
    unittest.main()

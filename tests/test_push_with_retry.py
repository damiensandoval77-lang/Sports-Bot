"""Exercise publishing races against a real local bare Git remote."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.push_with_retry import publish


class PublishRaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.writer = self.root / "writer"
        self.other = self.root / "other"
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.root, "clone", str(self.remote), str(self.writer))
        self.configure(self.writer)
        self.commit(self.writer, "shared.json", "original\n")
        self.git(self.writer, "push", "origin", "main")
        self.git(self.root, "clone", str(self.remote), str(self.other))
        self.configure(self.other)

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)

    def configure(self, cwd):
        self.git(cwd, "config", "user.name", "Test publisher")
        self.git(cwd, "config", "user.email", "test@example.invalid")

    def commit(self, cwd, filename, text):
        (cwd / filename).write_text(text)
        self.git(cwd, "add", filename)
        self.git(cwd, "commit", "-m", "Verified fixture update")

    def test_competing_commit_after_pull_is_preserved_and_retried(self):
        self.commit(self.writer, "boxscore.json", "verified stats\n")
        pushes = []
        def racing_run(cmd, **kwargs):
            if cmd[1] == "push":
                pushes.append(cmd)
                if len(pushes) == 1:
                    self.commit(self.other, "nba.json", "independent NBA update\n")
                    self.git(self.other, "push", "origin", "main")
            return subprocess.run(cmd, **kwargs, capture_output=True)
        self.assertEqual(publish(cwd=self.writer, run=racing_run), 2)
        self.git(self.other, "pull", "--ff-only")
        self.assertEqual((self.other / "boxscore.json").read_text(), "verified stats\n")
        self.assertEqual((self.other / "nba.json").read_text(), "independent NBA update\n")
        self.assertTrue(all("--force" not in cmd for cmd in pushes))

    def test_same_file_conflict_fails_without_overwriting_remote(self):
        self.commit(self.writer, "shared.json", "older capture\n")
        self.commit(self.other, "shared.json", "newer capture\n")
        self.git(self.other, "push", "origin", "main")
        before = self.git(self.other, "rev-parse", "HEAD").stdout
        def quiet_run(cmd, **kwargs):
            return subprocess.run(cmd, **kwargs, capture_output=True)
        with self.assertRaisesRegex(RuntimeError, "Cannot safely rebase"):
            publish(cwd=self.writer, run=quiet_run)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout, before)

    def test_repeated_push_failure_is_bounded_and_not_success(self):
        calls = []
        def rejected_run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 1 if cmd[1] == "push" else 0)
        with self.assertRaisesRegex(RuntimeError, "after 3"):
            publish(attempts=3, run=rejected_run)
        self.assertEqual(sum(c[1] == "push" for c in calls), 3)

    def test_shared_schedule_writers_serialize_and_checkout_current_main(self):
        # A retry cannot safely merge two generated one-line schedules. The
        # production writer contract must prevent that same-file race.
        root = Path(__file__).resolve().parents[1]
        workflows = [root / ".github/workflows" / name for name in
                     ("nfl-boxscores-publish.yml", "nfl-schedule-publish.yml")]
        groups = []
        for workflow in workflows:
            text = workflow.read_text()
            groups.append(next(line.strip() for line in text.splitlines() if line.strip().startswith("group:")))
            self.assertIn("cancel-in-progress: false", text)
            production = text.split("  boxscores:" if "boxscores-publish" in workflow.name else "  publish:",1)[1]
            self.assertIn("ref:", production)
            self.assertIn("main", production.split("ref:",1)[1].splitlines()[0])
        self.assertEqual(groups[0], groups[1])


if __name__ == "__main__":
    unittest.main()

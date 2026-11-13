"""Exercise the actual publisher shell with deterministic local push conflicts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/nba-tracking-coverage.yml'

class TrackingPublisherTests(unittest.TestCase):
    def execute(self, conflicts):
        text = WORKFLOW.read_text()
        step = text.split('      - name: Publish coverage without provider statistical rows\n', 1)[1]
        script = textwrap.dedent(step.split('        run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bin').mkdir()
            (root / 'docs').mkdir()
            fake = '''import json, os, pathlib, sys
root=pathlib.Path(os.environ['FAKE_ROOT'])
kind=pathlib.Path(sys.argv[0]).name
if kind=='git':
    if sys.argv[1:3]==['diff','--cached']:sys.exit(1)
    if sys.argv[1]=='push':
        p=root/'pushes'; n=int(p.read_text())+1 if p.exists() else 1;p.write_text(str(n))
        sys.exit(1 if n<=int(os.environ['CONFLICTS']) else 0)
elif kind=='python':
    p=root/'generations'; n=int(p.read_text())+1 if p.exists() else 1;p.write_text(str(n))
    (root/'docs/tracking_coverage_status.json').write_text(json.dumps({'generation':n}))
elif kind=='sleep':
    with (root/'waits').open('a') as f:f.write(sys.argv[1]+'\\n')
'''
            for name in ['git', 'python', 'sleep']:
                p = root / 'bin' / name
                p.write_text('#!' + sys.executable + '\n' + fake)
                p.chmod(0o755)
            env = {**os.environ, 'PATH': str(root/'bin') + os.pathsep + os.environ['PATH'],
                   'FAKE_ROOT': str(root), 'CONFLICTS': str(conflicts)}
            result = subprocess.run(['bash', '-c', script], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=20)
            pushes = int((root/'pushes').read_text())
            report = json.loads((root/'docs/tracking_coverage_status.json').read_text())
            waits = [int(v) for v in (root/'waits').read_text().splitlines()]
            return result, pushes, report, waits

    def test_recovers_after_three_conflicts_and_recomputes_latest_inputs(self):
        result, pushes, report, waits = self.execute(3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(pushes, 4)
        self.assertEqual(report['generation'], 4)
        self.assertEqual(len(waits), 3)
        self.assertTrue(all(2*i <= delay <= 2*i+2 for i, delay in enumerate(waits, 1)))

    def test_persistent_conflicts_fail_visibly_after_bounded_attempts(self):
        result, pushes, report, waits = self.execute(100)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(pushes, 10)
        self.assertEqual(report['generation'], 10)
        self.assertEqual(len(waits), 9)

    def test_pull_requests_cannot_publish(self):
        text = WORKFLOW.read_text()
        for name in ['Calculate research coverage from published board and grades',
                     'Publish coverage without provider statistical rows']:
            block = text.split('      - name: ' + name + '\n', 1)[1].split('      - name:', 1)[0]
            self.assertIn("if: github.event_name != 'pull_request'", block)

if __name__ == '__main__':
    unittest.main()

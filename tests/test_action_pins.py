"""Exercise the CI dependency trust boundary, including reusable/composite actions."""
import tempfile
import unittest
from pathlib import Path

from scripts.check_action_pins import audit, immutable_reference


class ActionPins(unittest.TestCase):
    def test_movable_tags_branches_expressions_and_short_shas_are_rejected(self):
        for ref in ('actions/checkout@v4', 'owner/repo@main', 'owner/repo@abc1234',
                    'owner/repo@${{ inputs.ref }}', 'docker://alpine:3',
                    'docker://alpine@sha256:abc', None, './', './../external',
                    './local/${{ inputs.action }}'):
            with self.subTest(ref=ref):
                self.assertFalse(immutable_reference(ref))

    def test_immutable_remote_container_and_local_references_are_accepted(self):
        for ref in ('actions/checkout@' + 'a' * 40,
                    'owner/repo/.github/workflows/build.yml@' + '1' * 40,
                    'actions/cache/restore@' + 'b' * 40,
                    'docker://alpine@sha256:' + 'c' * 64, './.github/actions/test'):
            with self.subTest(ref=ref):
                self.assertTrue(immutable_reference(ref))

    def test_reusable_jobs_and_composite_actions_cannot_escape_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = root / '.github/workflows'
            composite = root / '.github/actions/local'
            workflows.mkdir(parents=True)
            composite.mkdir(parents=True)
            (workflows / 'ci.yml').write_text('jobs:\n  reuse:\n    uses: owner/repo/.github/workflows/ci.yml@main\n')
            (composite / 'action.yaml').write_text('runs:\n  using: composite\n  steps:\n    - uses: actions/checkout@v4\n')
            files, references, problems = audit(root)
            self.assertEqual((files, references, len(problems)), (2, 2, 2))

    def test_empty_or_unparseable_audit_does_not_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertTrue(audit(root)[2])
            workflow = root / '.github/workflows/broken.yml'
            workflow.parent.mkdir(parents=True)
            workflow.write_text('jobs: [unterminated')
            self.assertTrue(audit(root)[2])

    def test_repository_has_no_mutable_action_dependencies(self):
        files, references, problems = audit()
        self.assertGreater(files, 0)
        self.assertGreater(references, 0)
        self.assertEqual(problems, [])


if __name__ == '__main__':
    unittest.main()

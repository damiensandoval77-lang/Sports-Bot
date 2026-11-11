import tempfile
import unittest
from pathlib import Path

from scripts.audit_workflow_topology import audit


class WorkflowTopologyAuditTests(unittest.TestCase):
    def test_detects_shared_concurrency_and_competing_data_writers(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            body="""name: test
on:
  workflow_dispatch:
  schedule:
    - cron: '3,18 * * * *'
permissions:
  contents: write
concurrency:
  group: nba-feed
  cancel-in-progress: false
jobs:
  publish:
    steps:
      - run: |
          git add docs/nba_player_tracking_independent.json
          git commit -m 'publish'
          git push origin HEAD:main
"""
            (base/"a.yml").write_text(body)
            (base/"b.yml").write_text(body)
            result=audit(base)
            self.assertEqual(result["workflow_files"],2)
            self.assertEqual(result["scheduled_workflows"],2)
            self.assertEqual(result["workflows_with_possible_git_writes"],2)
            self.assertEqual(result["shared_literal_concurrency_groups"]["nba-feed"],
                             ["a.yml","b.yml"])
            self.assertEqual(result["watched_multiwriter_targets"]
                ["docs/nba_player_tracking_independent.json"],["a.yml","b.yml"])

    def test_read_only_jobs_do_not_claim_writes_and_no_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            path=base/"readonly.yml"
            content="""on:
  schedule:
    - cron: '5 * * * *'
permissions:
  contents: read
concurrency:
  group: audit
jobs:
  check:
    steps:
      - run: cat docs/nba_player_tracking_independent.json
"""
            path.write_text(content)
            before=path.read_bytes()
            report=audit(base)
            self.assertEqual(report["watched_writer_inventory"],{})
            self.assertEqual(report["workflows_with_possible_git_writes"],0)
            self.assertEqual(path.read_bytes(),before)


if __name__=="__main__":
    unittest.main()

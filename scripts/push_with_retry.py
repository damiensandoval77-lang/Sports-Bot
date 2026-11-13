"""Publish an already committed change without overwriting concurrent work.

Only fast-forward pushes are permitted. Rebase conflicts and exhausted retries
are hard failures; callers must not suppress them or discard another writer.
"""
import subprocess
import sys


def publish(*, cwd=None, attempts=6, run=subprocess.run):
    if attempts < 1:
        raise ValueError("At least one publish attempt is required")
    def git(*args):
        return run(["git", *args], cwd=cwd, check=False).returncode
    for attempt in range(1, attempts + 1):
        if git("pull", "--rebase", "origin", "main"):
            raise RuntimeError("Cannot safely rebase publication; resolve conflict/access failure without overwriting main")
        if git("push", "origin", "HEAD:main") == 0:
            print(f"Published verified records on attempt {attempt}")
            return attempt
        print(f"Publication rejected on attempt {attempt}; retrying against current main", flush=True)
    raise RuntimeError(f"Publication failed after {attempts} non-force attempts")


if __name__ == "__main__":
    try:
        publish()
    except RuntimeError as error:
        print(f"::error::{error}", file=sys.stderr)
        sys.exit(1)

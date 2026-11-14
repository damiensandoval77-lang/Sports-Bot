"""Fail CI if a workflow or local composite action executes a mutable dependency."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REMOTE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*@[0-9a-f]{40}$")
CONTAINER = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")


def immutable_reference(value):
    if not isinstance(value, str) or "${{" in value:
        return False
    if value.startswith("./"):
        return bool(value[2:]) and ".." not in Path(value).parts and "@" not in value
    return bool(REMOTE.fullmatch(value) or CONTAINER.fullmatch(value))


def references(value, location=""):
    """Include reusable jobs and composite steps, not only ordinary job steps."""
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{location}.{key}" if location else str(key)
            if key == "uses":
                yield path, child
            else:
                yield from references(child, path)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from references(child, f"{location}[{i}]")


def audit(root=ROOT):
    files = set((root / ".github/workflows").glob("*.y*ml"))
    files.update((root / ".github/actions").rglob("action.y*ml"))
    problems = []
    count = 0
    for path in sorted(files):
        label = str(path.relative_to(root))
        try:
            document = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError) as error:
            problems.append(f"{label}: cannot verify action references: {error}")
            continue
        for location, ref in references(document):
            count += 1
            if not immutable_reference(ref):
                problems.append(f"{label}:{location}: mutable or invalid action reference {ref!r}")
    if not files:
        problems.append("No workflow files found; action dependency audit is incomplete")
    return len(files), count, problems


def main():
    files, count, problems = audit()
    for problem in problems:
        print(problem)
    print(f"Action pins: {files} definitions, {count} references, {len(problems)} violations")
    return bool(problems)


if __name__ == "__main__":
    sys.exit(main())

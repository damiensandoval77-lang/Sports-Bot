"""Read GitHub Actions step conditions and assert behavior instead of exact spelling.

This intentionally uses Python's standard library: PR publisher tests must
not need an extra YAML dependency before test imports.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def step(workflow,name):
    text=(ROOT/".github/workflows"/workflow).read_text()
    marker="      - name: "+name+"\n"
    if marker not in text:raise AssertionError(f"Missing workflow step: {workflow}: {name}")
    part=text.split(marker,1)[1].split("\n      - name:",1)[0]
    return {"run":part.split("\n        run:",1)[1] if "\n        run:" in part else "",
            "if":next((s.strip().removeprefix("if:").strip() for s in part.splitlines() if s.strip().startswith("if:")), "")}

def condition(workflow,name):return " ".join(step(workflow,name)["if"].split())
def runs_after_success(cond):
    return cond=="" or "success()" in cond or ("failure()" not in cond and "always()" not in cond)
def change_gated(cond):return "steps.publish.outputs.changed == 'true'" in cond
def excluded_from_pull_requests(cond):return "github.event_name != 'pull_request'" in cond

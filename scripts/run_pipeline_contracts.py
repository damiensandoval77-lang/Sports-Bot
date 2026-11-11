"""Run every PR-only unit-test command moved out of scheduled production workflows."""
import glob
import os
import re
import subprocess
import sys
import yaml

QUARANTINE={}
EXTRA=[
    "node --test iphone_bot/tests/test_coverage_banner.cjs",
    "python -m unittest iphone_bot.tests.test_pipeline_heartbeat -v",
    "python -m unittest iphone_bot.tests.test_espn_injury_void -v",
    "python -m unittest discover -s iphone_bot/tests -p 'test_model_dispatch_recovery.py' -v",
    "python -m unittest discover -s iphone_bot/tests -p 'test_pp_unchanged_snapshot_recovery.py' -v",
    "python -m unittest discover -s iphone_bot/tests -p 'test_prizepicks_pub_handoff.py' -v",
]
WRAPPED=re.compile(r'^if \[ "\$\{GITHUB_EVENT_NAME:-\}" = pull_request \]; then (.*); fi')
TEST=re.compile(r'^(python3? -m (py_compile|unittest|pytest)|node --(test|check)|pytest)\b')
def commands():
    seen={}
    for f in sorted(glob.glob(".github/workflows/*.yml")):
        data=yaml.safe_load(open(f)) or {}
        for job in (data.get("jobs") or {}).values():
            for step in job.get("steps",[]):
                cond=str(step.get("if","")).strip()
                pr_only=cond=="github.event_name == 'pull_request'"
                for raw in str(step.get("run","")).splitlines():
                    line=raw.strip()
                    wrapped=WRAPPED.match(line)
                    if wrapped:line=wrapped.group(1)
                    elif not pr_only:continue
                    if TEST.search(line) and line not in seen:
                        env={k:str(v).replace("${{ github.workspace }}",os.getcwd())
                             for k,v in (step.get("env") or {}).items()
                             if "${{" not in str(v).replace("${{ github.workspace }}","")}
                        seen[line]=(f,env)
    for line in EXTRA:seen.setdefault(line,("extra",{}))
    return [(cmd,*source) for cmd,source in seen.items()]
def main():
    failed=[];skipped=[];calls=commands()
    for cmd,wf,env in calls:
        reason=next((v for k,v in QUARANTINE.items() if k in cmd),None)
        if reason:skipped.append((cmd,reason));continue
        result=subprocess.run(cmd,shell=True,text=True,capture_output=True,env={**os.environ,**env})
        print(("PASS" if result.returncode==0 else "FAIL"),cmd,workflow if (workflow:=wf) else wf,flush=True)
        if result.returncode:
            failed.append(cmd)
            print((result.stdout+result.stderr)[-3500:],flush=True)
    for cmd,reason in skipped:print("QUARANTINED",cmd,reason)
    print("contract commands:",len(calls),"failed:",len(failed),"quarantined:",len(skipped))
    return 1 if failed else 0
if __name__=="__main__":sys.exit(main())

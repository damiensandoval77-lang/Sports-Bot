#!/usr/bin/env python3
"""Read-only audit of every tracked source and every GitHub Actions definition.
Static validation does not establish correct predictions or deployed freshness.
"""
from __future__ import annotations
import ast,datetime as dt,json,re,subprocess,sys
from collections import Counter,defaultdict
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"out"/"repo-audit"
OUT.mkdir(parents=True,exist_ok=True)
files=[Path(x.decode()) for x in subprocess.check_output(
    ["git","ls-files","-z"],cwd=ROOT).split(b"\0") if x]
paths={x.as_posix() for x in files}
findings=[]
stats=Counter()
workflow_index={}
edges=[]
def finding(severity,code,path,detail):
    findings.append({"severity":severity,"code":code,"path":str(path),"detail":str(detail)[:700]})
def cmdcheck(cmd,path):
    try:
        p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         text=True,timeout=30)
        if p.returncode:finding("ERROR","SOURCE_SYNTAX",path,(p.stderr or p.stdout)[-900:])
        return p.returncode==0
    except Exception as e:
        finding("ERROR","SOURCE_CHECK_CRASH",path,type(e).__name__+": "+str(e))
        return False
def trigger(data):
    return data.get("on",data.get(True,{}))
for path in files:
    name=path.as_posix()
    stats["tracked_files"]+=1
    ext=path.suffix.lower()
    stats["extension:"+ext]+=1
    if not (ROOT/path).is_file():continue
    if ext==".py":
        try:
            ast.parse((ROOT/path).read_text(encoding="utf-8"),filename=name)
            stats["python_ast_pass"]+=1
        except Exception as e:finding("ERROR","PYTHON_PARSE",name,e)
    elif ext in (".js",".mjs",".cjs"):
        if cmdcheck(["node","--check",name],name):stats["node_syntax_pass"]+=1
    elif ext==".json":
        try:
            json.loads((ROOT/path).read_text(encoding="utf-8"))
            stats["json_parse_pass"]+=1
        except Exception as e:finding("ERROR","JSON_PARSE",name,e)
    elif ext in (".sh",".bash"):
        if cmdcheck(["bash","-n",name],name):stats["bash_syntax_pass"]+=1

for path in sorted(x for x in files if x.as_posix().startswith(".github/workflows/")
                   and x.suffix.lower() in (".yml",".yaml")):
    name=path.as_posix()
    stats["workflows_total"]+=1
    try:data=yaml.safe_load((ROOT/path).read_text(encoding="utf-8"))
    except Exception as e:
        finding("ERROR","WORKFLOW_YAML_PARSE",name,e)
        continue
    if not isinstance(data,dict):
        finding("ERROR","WORKFLOW_NOT_MAPPING",name,"workflow YAML not a mapping")
        continue
    job_map=data.get("jobs",{})
    if not isinstance(job_map,dict) or not job_map:
        finding("ERROR","NO_JOBS",name,"workflow has no jobs")
        continue
    workflow_index[name]=data.get("name",path.stem)
    events=trigger(data)
    event_names=set(events.keys() if isinstance(events,dict)
                    else events if isinstance(events,list) else [events])
    stats["workflow_jobs"]+=len(job_map)
    if "schedule" in event_names:stats["scheduled_workflows"]+=1
    if "workflow_run" in event_names:stats["workflow_run_triggers"]+=1
    if "pull_request" in event_names:stats["pr_workflows"]+=1
    if "workflow_dispatch" in event_names:stats["manually_dispatchable"]+=1
    if "pull_request_target" in event_names:
        finding("WARN","PR_TARGET_PRIVILEGE",name,"Inspect untrusted PR trust boundary")
    if not event_names:finding("WARN","NO_EVENT",name,"No recognized workflow event")
    if data.get("permissions")=="write-all":
        finding("WARN","BROAD_PERMISSIONS",name,"Workflow has write-all permissions")
    for job_name,job in job_map.items():
        if not isinstance(job,dict):
            finding("ERROR","JOB_NOT_MAPPING",name,job_name)
            continue
        needs=job.get("needs",[])
        if isinstance(needs,str):needs=[needs]
        for n in needs or []:
            if n not in job_map:
                finding("ERROR","MISSING_JOB_DEPENDENCY",name,str(job_name)+" needs "+str(n))
        local_reusable=str(job.get("uses",""))
        if local_reusable.startswith("./") and local_reusable[2:] not in paths:
            finding("ERROR","MISSING_LOCAL_ACTION",name,local_reusable)
        for i,step in enumerate(job.get("steps",[]) or []):
            if not isinstance(step,dict):
                finding("ERROR","BAD_STEP",name,str(job_name)+"["+str(i)+"]")
                continue
            stats["workflow_steps"]+=1
            uses=str(step.get("uses",""))
            if uses.startswith("./") and uses[2:] not in paths and not any(
                    p.startswith(uses[2:].rstrip("/")+"/") for p in paths):
                finding("ERROR","MISSING_LOCAL_ACTION",name,uses)
            if uses and "@" in uses and not uses.startswith("./"):
                if not re.fullmatch("[a-f0-9]{40}",uses.split("@")[-1]):
                    stats["actions_not_sha_pinned"]+=1
            cond=str(step.get("if",""))
            run=str(step.get("run",""))
            if any(x in event_names for x in ("schedule","workflow_dispatch","workflow_run")):
                if re.search(r"(?:python(?:3)? -m (?:unittest|pytest)|node --test|pytest )",run):
                    if "pull_request" not in cond and not re.search(
                            r"GITHUB_EVENT_NAME[^\n]{0,80}pull_request",run):
                        stats["runtime_test_commands_unguarded_steps"]+=1
                        if stats["runtime_test_commands_unguarded_steps"]<=45:
                            finding("WARN","PRODUCTION_UNIT_TEST_GATE",name,
                                    str(job_name)+": "+str(step.get("name",i)))
            if step.get("continue-on-error") is True:stats["continue_on_error_steps"]+=1
            for m in re.finditer(r"\bgh\s+workflow\s+run\s+([A-Za-z0-9_.-]+)",run):
                edges.append({"from":name,"to":m.group(1),"type":"dispatch"})
            if re.search(r"git\s+push\b",run):stats["workflow_push_steps"]+=1
    if isinstance(events,dict) and isinstance(events.get("workflow_run"),dict):
        for source in events["workflow_run"].get("workflows",[]):
            edges.append({"from":source,"to":name,"type":"workflow_run"})

names=set(workflow_index.values())
by_file={x.split("/")[-1]:x for x in workflow_index}
for edge in edges:
    if edge["type"]=="dispatch" and edge["to"] not in by_file:
        finding("ERROR","MISSING_DISPATCH_TARGET",edge["from"],edge["to"])
    elif edge["type"]=="workflow_run" and edge["from"] not in names and edge["from"]!="pages build and deployment":
        finding("WARN","MISSING_WORKFLOW_NAME_REFERENCE",edge["to"],edge["from"])
name_to_files=defaultdict(list)
for f,display in workflow_index.items():name_to_files[display].append(f)
for name,matches in name_to_files.items():
    if len(matches)>1:
        finding("WARN","DUPLICATE_WORKFLOW_NAME",",".join(matches),name)

data_evidence={}
for f in ("docs/nightly_grade_health.json","docs/tonight_capture_gradeability.json",
          "docs/production_readiness.json","docs/pregame_lifecycle_readiness.json",
          "docs/lagged_matchup_live_all_markets.json","docs/dames-picks/release.json",
          "docs/dames-picks/unified_readiness.json"):
    p=ROOT/f
    if not p.exists():
        data_evidence[f]={"present":False}
        continue
    try:
        d=json.loads(p.read_text())
        data_evidence[f]={"present":True,
          "status":d.get("status"),"generated_at":d.get("generated_at"),
          "checked_at":d.get("checked_at"),"release_id":d.get("release_id"),
          "failures":d.get("failures") or d.get("issues")}
        if f.endswith("nightly_grade_health.json"):
            data_evidence[f].update({k:d.get(k) for k in (
                "ai_forecasts_recorded","ai_forecasts_ungraded","ai_forecasts_graded")})
    except Exception as e:data_evidence[f]={"present":True,"parse_error":str(e)}
findings.sort(key=lambda x:({"ERROR":0,"WARN":1,"INFO":2}.get(x["severity"],3),x["code"],x["path"]))
report={"repository":"damiensandoval77-lang/Sports-Bot",
    "audited_ref":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    "checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
    "scope":"Every tracked Python, JS, JSON, shell and workflow YAML source file; static validation",
    "counts":dict(stats),"workflow_names":workflow_index,
    "workflow_edges":edges,"data_evidence":data_evidence,
    "findings":findings,"errors":sum(x["severity"]=="ERROR" for x in findings),
    "warnings":sum(x["severity"]=="WARN" for x in findings)}
(OUT/"audit.json").write_text(json.dumps(report,indent=2)+"\n")
md=["# Repository-wide read-only static audit",
    "Revision: "+report["audited_ref"],"Checked: "+report["checked_at"],
    "Tracked files: "+str(stats["tracked_files"])+"; workflows: "+str(stats["workflows_total"]),
    "Workflow jobs: "+str(stats["workflow_jobs"])+"; steps: "+str(stats["workflow_steps"]),
    "Python parse passed: "+str(stats["python_ast_pass"])+"; JS syntax passed: "+str(stats["node_syntax_pass"]),
    "Static errors: "+str(report["errors"])+"; warnings: "+str(report["warnings"]),
    "Static checks cannot guarantee live feeds, numeric forecasting validity or iPhone Safari parity.",
    "## Committed data-health evidence",json.dumps(data_evidence,indent=2),"## Findings"]
for f in findings[:300]:
    md.append("- "+f["severity"]+" / "+f["code"]+" : "+f["path"]+" : "+f["detail"])
(OUT/"audit.md").write_text("\n".join(md)+"\n")
print(json.dumps({k:report[k] for k in ("audited_ref","counts","errors","warnings")},indent=2))
for f in findings[:35]:print(f["severity"],f["code"],f["path"],f["detail"][:120])
print("Reports: out/repo-audit/audit.json and audit.md")
sys.exit(1 if report["errors"] else 0)

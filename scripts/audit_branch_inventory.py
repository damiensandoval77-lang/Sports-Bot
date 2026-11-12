#!/usr/bin/env python3
"""Inventory ALL remote branches with head SHA, PR association and divergence.

Never checks out or merges a branch. No writes to remote. Save every result,
including API failures, so coverage cannot silently appear complete.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json,os,time,sys
OWNER="damiensandoval77-lang"
REPO="Sports-Bot"
API="https://api.github.com/repos/"+OWNER+"/"+REPO
TOKEN=os.environ.get("GITHUB_TOKEN","")
OUT=Path("out/repo-audit")
OUT.mkdir(parents=True,exist_ok=True)
def get(path,timeout=24):
    url=API+path
    req=Request(url,headers={
        "Accept":"application/vnd.github+json",
        "User-Agent":"DamesPicks-BranchInventory/1.0",
        **({"Authorization":"Bearer "+TOKEN} if TOKEN else {})})
    with urlopen(req,timeout=timeout) as response:
        return json.loads(response.read())
def page_all(kind):
    rows=[]
    for page in range(1,30):
        r=get("/"+kind+("?" if "?" not in kind else "&")+"per_page=100&page="+str(page))
        if not isinstance(r,list):raise ValueError("Unexpected "+kind+" response")
        rows.extend(r)
        if len(r)<100:break
    return rows
branches=page_all("branches")
prs=page_all("pulls?state=open")
active={p["head"]["ref"]:[] for p in prs if p.get("head",{}).get("repo",{}).get("full_name")==OWNER+"/"+REPO}
for p in prs:
    name=p.get("head",{}).get("ref")
    if name in active:active[name].append(p["number"])
main=next((b for b in branches if b["name"]=="main"),None)
if not main:raise RuntimeError("main branch missing")
base_sha=main["commit"]["sha"]
def inspect(b):
    name=b["name"]
    item={"branch":name,"sha":b["commit"]["sha"],
          "protected":bool(b.get("protected")),
          "open_prs":active.get(name,[]),
          "same_as_main":b["commit"]["sha"]==base_sha}
    if name=="main":
        item["divergence"]="BASE"
        return item
    # GitHub's compare endpoint provides the correct merge base even when
    # a branch was already squash-merged and its head SHA differs from main.
    encoded=quote(name,safe="")
    try:
        d=get("/compare/main..."+encoded,timeout=32)
        item.update({"divergence":d.get("status"),"ahead_by":d.get("ahead_by"),
                     "behind_by":d.get("behind_by"),
                     "merge_base":(d.get("merge_base_commit") or {}).get("sha"),
                     "total_commits":d.get("total_commits")})
    except Exception as error:
        item["divergence"]="UNVERIFIED"
        item["error"]=type(error).__name__+":"+str(error)[:160]
    return item
rows=[]
with ThreadPoolExecutor(max_workers=5) as pool:
    for completed in as_completed([pool.submit(inspect,b) for b in branches]):
        rows.append(completed.result())
rows.sort(key=lambda x:x["branch"])
status={}
for x in rows:status[x["divergence"]]=status.get(x["divergence"],0)+1
report={"checked_at":datetime.now(timezone.utc).isoformat(),"main_sha":base_sha,
    "branch_count":len(rows),"open_pr_count":len(prs),
    "checked_branch_count":sum(x["divergence"]!="UNVERIFIED" for x in rows),
    "unverified_count":sum(x["divergence"]=="UNVERIFIED" for x in rows),
    "statuses":status,"branches":rows,
    "warning":"Compare status reflects Git ancestry, NOT feature correctness or safe mergeability."}
(OUT/"branch-inventory.json").write_text(json.dumps(report,indent=2)+"\n")
with (OUT/"branch-inventory.md").open("w") as f:
    f.write("# Full branch inventory\n\n")
    f.write("Branches: "+str(len(rows))+"; checked: "+str(report["checked_branch_count"])+"; unverified: "+str(report["unverified_count"])+"\n")
    f.write("Main SHA: "+base_sha+"\n\n")
    for k,v in sorted(status.items()):f.write("- "+k+": "+str(v)+"\n")
    f.write("\n## Each branch\n\n")
    for x in rows:
        f.write("- "+x["branch"]+" | "+str(x["divergence"])+" | ahead="+str(x.get("ahead_by"))+
            " behind="+str(x.get("behind_by"))+" | openPR="+str(x["open_prs"])+
            (" | "+x.get("error","") if x["divergence"]=="UNVERIFIED" else "")+"\n")
print(json.dumps({k:report[k] for k in ("checked_at","main_sha","branch_count",
    "open_pr_count","checked_branch_count","unverified_count","statuses")},indent=2))
for x in rows:
    if x["divergence"]=="UNVERIFIED":print("UNVERIFIED",x["branch"],x.get("error"))
sys.exit(1 if report["unverified_count"] else 0)

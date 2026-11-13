#!/usr/bin/env python3
"""Inventory ALL remote branches with head SHA, PR association and divergence.

Never checks out or merges a branch. No writes to remote. Save every result,
including API failures, so coverage cannot silently appear complete.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
import json,os,sys
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
    for page in range(1,101):
        separator="?" if "?" not in kind else "&"
        batch=get(f"/{kind}{separator}per_page=100&page={page}")
        if not isinstance(batch,list):
            raise ValueError("Unexpected "+kind+" response")
        rows.extend(batch)
        if len(batch)<100:
            return rows
    raise RuntimeError("Pagination limit reached; inventory would be incomplete")

branches=page_all("branches")
prs=page_all("pulls?state=all")
related={}
for pr in prs:
    head=pr["head"]
    if (head.get("repo") or {}).get("full_name")==OWNER+"/"+REPO:
        related.setdefault(head["ref"],[]).append(pr)
main=next((branch for branch in branches if branch["name"]=="main"),None)
if not main:
    raise RuntimeError("main branch missing")
base_sha=main["commit"]["sha"]

live_tips={(branch["name"],branch["commit"]["sha"]) for branch in branches}
historical={}
for name, history in related.items():
    for pr in history:
        key=(name,pr["head"]["sha"])
        if key not in live_tips:
            historical[key]={"name":name,"commit":{"sha":key[1]},"historical_pr_tip":True}

def inspect(b):
    name=b["name"]
    sha=b["commit"]["sha"]
    historical_tip=b.get("historical_pr_tip",False)
    history=related.get(name,[])
    item={"branch":name,"sha":sha,
          "historical_pr_tip":historical_tip,
          "protected":b.get("protected"),
          "open_prs":[p["number"] for p in history if p["state"]=="open" and p["head"]["sha"]==sha],
          "merged_prs":[p["number"] for p in history if p.get("merged_at") and p["head"]["sha"]==sha and p["base"]["ref"]=="main"],
          "same_as_main":sha==base_sha}
    if name=="main" and not historical_tip:
        item["divergence"]="BASE"
        return item
    # GitHub's compare endpoint provides the correct merge base even when
    # a branch was already squash-merged and its head SHA differs from main.
    try:
        d=get("/compare/"+base_sha+"..."+sha,timeout=32)
        if d.get("status") not in {"identical","ahead","behind","diverged"} or not d.get("merge_base_commit",{}).get("sha"):
            raise ValueError("Incomplete comparison response")
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
    for completed in as_completed([pool.submit(inspect,b) for b in [*branches,*historical.values()]]):
        rows.append(completed.result())
rows.sort(key=lambda x:(x["branch"],x["historical_pr_tip"],x["sha"]))
status={}
for x in rows:status[x["divergence"]]=status.get(x["divergence"],0)+1
report={"checked_at":datetime.now(timezone.utc).isoformat(),"main_sha":base_sha,
    "branch_count":len(branches),"historical_pr_tip_count":len(historical),
    "open_pr_count":sum(p["state"]=="open" for p in prs),
    "main_protected":main.get("protected"),
    "checked_branch_count":sum(x["divergence"]!="UNVERIFIED" for x in rows),
    "unverified_count":sum(x["divergence"]=="UNVERIFIED" for x in rows),
    "statuses":status,"branches":rows,
    "warning":"Compare status reflects Git ancestry, NOT feature correctness or safe mergeability."}
(OUT/"branch-inventory.json").write_text(json.dumps(report,indent=2)+"\n")
with (OUT/"branch-inventory.md").open("w") as f:
    f.write("# Full branch inventory\n\n")
    f.write("Current branches and historical PR tips: "+str(len(rows))+"; checked: "+str(report["checked_branch_count"])+"; unverified: "+str(report["unverified_count"])+"\n")
    f.write("Main SHA: "+base_sha+"\n\n")
    for k,v in sorted(status.items()):f.write("- "+k+": "+str(v)+"\n")
    f.write("\n## Each branch\n\n")
    for x in rows:
        f.write("- "+x["branch"]+" @ "+x["sha"]+" | historical="+str(x["historical_pr_tip"])+" | "+str(x["divergence"])+" | ahead="+str(x.get("ahead_by"))+
            " behind="+str(x.get("behind_by"))+" | openPR="+str(x["open_prs"])+" | mergedPR="+str(x["merged_prs"])+
            (" | "+x.get("error","") if x["divergence"]=="UNVERIFIED" else "")+"\n")
print(json.dumps({k:report[k] for k in ("checked_at","main_sha","branch_count",
    "historical_pr_tip_count","main_protected","open_pr_count","checked_branch_count","unverified_count","statuses")},indent=2))
for x in rows:
    if x["divergence"]=="UNVERIFIED":print("UNVERIFIED",x["branch"],x.get("error"))
sys.exit(1 if report["unverified_count"] else 0)

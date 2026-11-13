"""Inspect public Kaggle NBA dataset metadata without credentials or full download.

No API key, no paid calls, no training promotion. Do not confuse moneyline
history with player prop prices or NBA player tracking chances.
"""
import json,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
URL="https://www.kaggle.com/api/v1/datasets/view/chevronronson/nba-stats-dataset"
OUTPUT=ROOT/"docs/kaggle_nba_stats_source_audit.json"
MARKET_KEYS=("odds","moneyline","spread","total","opening","closing","movement","price")
PLAYER_KEYS=("player","assist","rebound","potential","tracking","stat")

def assess(meta):
    rawfiles=meta.get("resources") or meta.get("files") or []
    files=[]
    for f in rawfiles:
        if not isinstance(f,dict):continue
        name=str(f.get("ref") or f.get("name") or f.get("fileName") or "")
        filesize=f.get("totalBytes") or f.get("size") or f.get("total_bytes")
        if name:files.append({"name":name,"bytes":filesize})
    names=" ".join(x["name"].lower() for x in files)
    license_data=meta.get("licenseName") or meta.get("license") or ""
    if isinstance(license_data,dict):license_data=license_data.get("name") or license_data.get("id") or ""
    return {
        "status":"PUBLIC_METADATA_AVAILABLE",
        "slug":"chevronronson/nba-stats-dataset",
        "title":meta.get("title"),"version":meta.get("currentVersionNumber"),
        "last_updated":meta.get("lastUpdated") or meta.get("last_updated"),
        "license_reported":license_data,
        "file_list":files[:150],"file_count":len(files),
        "files_list_complete":bool(files),
        "likely_market_files":[x["name"] for x in files
                               if any(v in x["name"].lower() for v in MARKET_KEYS)],
        "likely_player_files":[x["name"] for x in files
                               if any(v in x["name"].lower() for v in PLAYER_KEYS)],
        "can_confirm_player_tracking_columns":False,
        "can_confirm_moneyline_columns":False,
        "production_model_changed":False,
        "ready_to_import":False,
        "next":"Inspect actual file headers and data license; never promote features without out-of-time validation."
    }
def main():
    report={"status":"METADATA_UNAVAILABLE",
            "slug":"chevronronson/nba-stats-dataset",
            "checked_at":datetime.now(timezone.utc).isoformat(),
            "production_model_changed":False,"ready_to_import":False}
    try:
        req=urllib.request.Request(URL,headers={"Accept":"application/json",
                        "User-Agent":"Sports-Bot-source-audit/1.0"})
        with urllib.request.urlopen(req,timeout=20) as resp:
            payload=json.load(resp)
        if not isinstance(payload,dict):raise ValueError("Invalid Kaggle metadata")
        report={**report,**assess(payload)}
    except (urllib.error.URLError,TimeoutError,ValueError,TypeError) as e:
        report["error_type"]=type(e).__name__
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("Kaggle metadata audit:",report["status"],"files:",report.get("file_count",0),
          "license:",report.get("license_reported","unknown"))
if __name__=="__main__":main()

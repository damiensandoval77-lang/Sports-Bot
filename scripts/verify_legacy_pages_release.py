"""Read-only byte-for-byte proof of the actual legacy GitHub Pages release.

Never changes Pages settings. Native Pages source should be allowed to deploy
from main; the runner verifies the served release ID and every pinned asset.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE="https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/"
MANIFEST=ROOT/"docs/dames-picks/release.json"

def git_blob_sha(content):
    return hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()

def fetch(name):
    # A unique query avoids a stale intermediary cache while using normal
    # GitHub Pages read-only HTTPS endpoints.
    stamp=int(dt.datetime.now(dt.timezone.utc).timestamp())
    req=urllib.request.Request(BASE+name+"?release_audit="+str(stamp),
       headers={"Cache-Control":"no-cache","User-Agent":"DamesPicks-SourceModeVerifier"})
    with urllib.request.urlopen(req,timeout=25) as response:return response.read()

def evaluate(expected,served,assets):
    checks=[{"name":"release_id_matches_main",
             "pass":served.get("release_id")==expected.get("release_id")},
            {"name":"release_manifest_exact_match",
             "pass":served==expected}]
    for filename,digest in expected.get("asset_blob_sha1",{}).items():
        blob=assets.get(filename)
        checks.append({"name":"served_asset_"+filename,
                       "pass":bool(blob is not None and git_blob_sha(blob)==digest),
                       "expected":digest,"actual":git_blob_sha(blob) if blob is not None else None})
    checks.append({"name":"all_pinned_assets_listed",
                   "pass":set(expected.get("asset_blob_sha1",{}))==
                   {"feeds.js","live_direct.js","dames_take.js","provisional.js","index.html"}})
    return {"expected_release":expected.get("release_id"),
            "served_release":served.get("release_id"),
            "checks":checks,"status":"PASS" if all(x["pass"] for x in checks) else "FAIL"}

def main():
    out=Path(sys.argv[1] if len(sys.argv)>1 else "pages-release-verification.json")
    expected=json.loads(MANIFEST.read_text())
    evidence={}
    for attempt in range(1,4):
        try:
            served=json.loads(fetch("release.json"))
            assets={name:fetch(name) for name in expected.get("asset_blob_sha1",{})}
            evidence=evaluate(expected,served,assets)
            evidence["attempt"]=attempt
            if evidence["status"]=="PASS":break
        except Exception as err:
            evidence={"status":"FAIL","attempt":attempt,
                      "error":type(err).__name__+": "+str(err)[:250]}
        if attempt<3:time.sleep(12)
    evidence["checked_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
    evidence["source_mode"]="legacy_branch"
    evidence["note"]="Verifies native Pages deployment; does NOT claim GitHub Actions deploy-pages was run."
    out.write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps(evidence,indent=2))
    return 0 if evidence["status"]=="PASS" else 1

if __name__=="__main__":sys.exit(main())

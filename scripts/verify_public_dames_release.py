"""Read-only deployment gate: main != released until public Pages bytes match.

No GitHub API writes, provider calls, or database changes. A pass proves
the public HTTP service is serving this checkout's UI/JS, not that a user's
individual browser cache has refreshed or live betting data is correct.
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE="https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/"
FILES=("index.html","feeds.js","live_direct.js","dames_take.js","release.json")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(expected, observed):
    reasons=[]
    for name in FILES:
        if name not in observed:
            reasons.append(name+": PUBLIC_FILE_UNAVAILABLE")
        elif expected.get(name)!=observed[name]:
            reasons.append(name+": PUBLIC_FILE_DIFFERS_FROM_CHECKED_OUT_MAIN")
    html=observed.get("index.html",b"")
    if b"SIM EST." in html or b"Sim est." in html:
        reasons.append("PUBLIC_OLD_SIM_ESTIMATE_LABEL")
    if b"HIT EST." not in html or b"Hit est." not in html:
        reasons.append("PUBLIC_NEW_HIT_ESTIMATE_LABEL_MISSING")
    try:
        published=json.loads(observed.get("release.json",b""))
        expected_release=json.loads(expected["release.json"])
        if published.get("release_id")!=expected_release.get("release_id"):
            reasons.append("RELEASE_ID_MISMATCH")
        if expected_release["release_id"].encode() not in html:
            reasons.append("PUBLIC_HTML_RELEASE_ID_MISSING")
    except (KeyError,ValueError,TypeError):
        reasons.append("PUBLIC_RELEASE_MANIFEST_INVALID")
    return reasons


def fetch_public(base, now):
    found={}
    for name in FILES:
        url=base.rstrip("/")+"/"+name+"?v="+str(now)
        request=urllib.request.Request(url,headers={
            "User-Agent":"DamesPicks-Release-Probe/1.0",
            "Cache-Control":"no-cache","Pragma":"no-cache"})
        with urllib.request.urlopen(request,timeout=18) as response:
            if response.status!=200:
                raise IOError(name+" returned HTTP "+str(response.status))
            found[name]=response.read()
    # Users normally open the folder root, not explicit index.html.
    request=urllib.request.Request(base.rstrip("/")+"/?v="+str(now),
              headers={"User-Agent":"DamesPicks-Release-Probe/1.0",
                       "Cache-Control":"no-cache","Pragma":"no-cache"})
    with urllib.request.urlopen(request,timeout=18) as response:
        if response.status!=200:raise IOError("folder root returned "+str(response.status))
        found["folder-root.html"]=response.read()
    return found


def evaluate(expected,remote):
    errors=inspect(expected,remote)
    if remote.get("folder-root.html")!=expected["index.html"]:
        errors.append("PUBLIC_FOLDER_ROOT_IS_STALE")
    return errors


def run(local,base,timeout_seconds=600,interval_seconds=30):
    expected={p:(local/p).read_bytes() for p in FILES}
    start=time.monotonic()
    report={"public_url":base,"expected_release":json.loads(expected["release.json"])["release_id"],
            "mode":"PUBLIC_HTTP_BYTE_FOR_BYTE_CHECK","state":"BLOCKED","reasons":[]}
    attempts=0
    while True:
        attempts+=1
        try:
            remote=fetch_public(base,int(time.time()))
            problems=evaluate(expected,remote)
            report["public_files"]={k:digest(v) for k,v in remote.items()}
            report["local_files"]={k:digest(v) for k,v in expected.items()}
        except (IOError,ValueError,urllib.error.URLError,TimeoutError) as exc:
            problems=["PUBLIC_FETCH_FAILED:"+str(exc)[:200]]
        report["attempts"]=attempts
        report["reasons"]=problems
        if not problems:
            report["state"]="DEPLOYED_BYTES_VERIFIED"
            break
        if time.monotonic()-start>=timeout_seconds:
            break
        print("Awaiting public Pages deployment:",", ".join(problems),flush=True)
        time.sleep(min(interval_seconds,max(0,timeout_seconds-(time.monotonic()-start))))
    print(json.dumps(report,indent=2,sort_keys=True),flush=True)
    return 0 if report["state"]=="DEPLOYED_BYTES_VERIFIED" else 2


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--local",default="docs/dames-picks")
    parser.add_argument("--base",default=BASE)
    parser.add_argument("--timeout-seconds",type=int,default=600)
    args=parser.parse_args()
    raise SystemExit(run(Path(args.local),args.base,args.timeout_seconds))


if __name__=="__main__":
    main()

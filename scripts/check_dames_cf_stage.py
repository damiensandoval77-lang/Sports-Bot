#!/usr/bin/env python3
"""Verify REAL Cloudflare staging site without paid APIs or modifying production."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE=os.environ.get("DAMES_CF_STAGE_URL","https://dames-picks-staging.damiensandoval77.workers.dev").rstrip("/")
def get(path):
    url=BASE+path+("?" if "?" not in path else "&")+"staging_check="+str(int(time.time()))
    req=urllib.request.Request(url,headers={
        "User-Agent":"DamesPicks-Staging-ReleaseAudit/1",
        "Cache-Control":"no-cache","Accept":"application/json,text/html,*/*"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            return r.status,r.read(1600000).decode("utf-8","replace"),r.headers
    except urllib.error.HTTPError as e:
        return e.code,e.read(1600000).decode("utf-8","replace"),e.headers

def main():
    print("Verifying external Cloudflare Workers site",BASE,flush=True)
    status,body,headers=get("/healthz")
    print("GET /healthz:",status,body[:850],flush=True)
    assert status==200,("Worker health endpoint failed",status,body[:500])
    health=json.loads(body)
    assert health["service"]=="dames-picks-staging",health
    assert health["stage"]=="staging",health
    assert health["worker_reachable"] is True,health
    assert health["provider_collection_active"] is False,health
    assert health["paid_provider_calls"]=="disabled",health

    status,body,headers=get("/api/v1/status")
    print("GET /api/v1/status:",status,body[:1800],flush=True)
    assert status in (200,503),("Unexpected status response",status,body[:600])
    state=json.loads(body)
    assert state["service"]=="dames-picks-staging",state
    assert state["status"] in ("setup_required","collectors_not_ready"),state
    if status==503:
        assert state["database"]=="not_bound",state
    if status==200:
        assert state["database"]=="connected",state
        assert state["automatic_collectors"]=="not_connected",state
        assert len(state.get("sources",[]))==7,state

    status,body,headers=get("/dames-picks/")
    print("GET /dames-picks/:",status,"html bytes",len(body),flush=True)
    assert status==200 and "Dame" in body,("Staged page inaccessible",status,body[:400])
    assert "cloudflare-staging-banner" in body, "Not a clearly identified staging build"
    assert "dp-concept3-unified-20261117-r1" in body,"Wrong homepage release"
    assert "noindex,nofollow" in body,"Staging indexing guard absent"

    status,body,headers=get("/dames-picks/classic.html")
    print("GET /dames-picks/classic.html:",status,"bytes",len(body),flush=True)
    assert status==200 and 'data-view="tracker"' in body and 'data-league="TENNIS"' in body, "Original bot UI unavailable"
    for path,needed in [
       ("/dames-picks/feeds.js","DamesPicksModel"),
       ("/dames-picks/concept-3-connected.js","DamesConcept3Status"),
       ("/dames-picks/unified-shell.js","DamesUnifiedUI"),
       ("/nba_schedule.json","games"),
       ("/current_form.json","players")
    ]:
        code,text,headers=get(path)
        print("GET",path,code,"bytes",len(text),flush=True)
        assert code==200,("Staging missing critical file",path,code,text[:150])
        assert needed in text,("Unexpected or empty file",path)
    print("PASS CLOUDFLARE STAGING: Worker reachable, cost guard enabled, database readiness truthful, site and preserved tools served.",flush=True)
    print("LIMIT: static game-data snapshots are NOT yet independently auto-refreshed by Cloudflare; D1/odds/prediction automation remains a separate milestone.",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("STAGING VERIFICATION FAILED:",type(e).__name__,str(e)[:1800],file=sys.stderr,flush=True)
        raise

#!/usr/bin/env python3
"""Read-only live probe for the exact Dame's Picks Cloudflare staging D1.
Checks deployment/binding and reports Cron schema/heartbeat separately.
No API keys, no paid-provider calls, no writes and no Federal Briefing access.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE=os.getenv("DAMES_CF_STAGING","https://dames-picks-staging.damiensandoval77.workers.dev").rstrip("/")
EXPECTED=("nba_scores","nba_player_stats","nfl_scores","nfl_player_stats",
          "prizepicks_standard_lines","frozen_ai_projections","postgame_grades")

def fetch(path):
    req=urllib.request.Request(BASE+path+"?d1_probe="+str(int(time.time())),headers={
        "Accept":"application/json","Cache-Control":"no-cache",
        "User-Agent":"DamesPicks-Staging-D1-Readiness/1"})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:return r.status,json.loads(r.read(200000))
    except urllib.error.HTTPError as e:
        return e.code,json.loads(e.read(200000))
def scan():
    h_code,health=fetch("/healthz")
    s_code,status=fetch("/api/v1/status")
    assert h_code==200 and health.get("service")=="dames-picks-staging",("Wrong Worker or health",h_code,health)
    assert health.get("paid_provider_calls")=="disabled" and not health.get("provider_collection_active"),"Unexpected paid-provider activity"
    assert status.get("service")=="dames-picks-staging",("Wrong status service",status)
    print("HEALTH",h_code,json.dumps(health),flush=True)
    print("STATUS",s_code,json.dumps(status)[:4000],flush=True)
    assert health.get("database_binding_present") is True,"D1 binding not active in current deployed Worker"
    if s_code==503:
        assert status.get("status")=="database_unavailable",("Unexpected D1 response",s_code,status)
        return "binding_active_schema_pending"
    assert s_code==200 and status.get("database")=="connected",("D1 database error",s_code,status)
    rows=status.get("sources") or []
    missing=set(EXPECTED)-{r.get("source") for r in rows}
    assert not missing,("Missing expected source rows",sorted(missing))
    assert status.get("automatic_collectors")=="not_connected",("Unexpected automatic collectors",status)
    hb=status.get("scheduled_heartbeat")
    if not hb:return "schema_ready_awaiting_heartbeat"
    assert hb.get("job")=="staging-heartbeat" and hb.get("outcome")=="success",hb
    timestamp=hb.get("completed_at") or hb.get("scheduled_at")
    when=dt.datetime.fromisoformat(str(timestamp).replace("Z","+00:00"))
    if when.tzinfo is None:when=when.replace(tzinfo=dt.timezone.utc)
    age=(dt.datetime.now(dt.timezone.utc)-when).total_seconds()
    assert -180<=age<=3600,("Heartbeat is outside the expected window",age,hb)
    return "schema_and_heartbeat_verified"

def main():
    wait=int(os.getenv("DAMES_CF_BINDING_WAIT_SECONDS","120"))
    deadline=time.monotonic()+wait
    last=None
    while True:
        try:
            state=scan()
            print("STAGING_D1_STATE",state,flush=True)
            return 0
        except Exception as e:
            last=f"{type(e).__name__}: {e}"
            if time.monotonic()+12>=deadline:break
            print("Not yet deployed or bound; retrying:",last[:450],flush=True)
            time.sleep(12)
    print("D1 LIVE CHECK FAILED",last,file=sys.stderr,flush=True)
    return 1
if __name__=="__main__":sys.exit(main())

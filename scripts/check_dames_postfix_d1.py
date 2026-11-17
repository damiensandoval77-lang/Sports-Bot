#!/usr/bin/env python3
"""Read-only proof that Cloudflare deployed the bound D1 and internal Cron ran.
No Cloudflare token, provider secret, API purchase or database mutation.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT="https://dames-picks-staging.damiensandoval77.workers.dev"
OUT=Path("test-artifacts/dames-d1-postfix-proof.json")

def fetch(path):
    request=urllib.request.Request(ROOT+path+"?qa="+str(int(time.time())),headers={
      "Accept":"application/json","Cache-Control":"no-cache",
      "User-Agent":"DamesPicks-D1-ExternalReadOnlyVerifier"})
    try:
      with urllib.request.urlopen(request,timeout=20) as response:
        return response.status, json.load(response)
    except urllib.error.HTTPError as error:
      return error.code, json.loads(error.read().decode("utf-8","replace"))

def verify():
    hcode,health=fetch("/healthz")
    scode,status=fetch("/api/v1/status")
    print("CLOUDFLARE D1 LIVE HTTP",hcode,scode,flush=True)
    print("Health:",json.dumps(health,sort_keys=True),flush=True)
    print("Status:",json.dumps(status,sort_keys=True)[:5000],flush=True)
    ocode,odds=fetch("/api/v1/odds/budget")
    print("Odds D1 cache:",ocode,json.dumps(odds,sort_keys=True)[:900],flush=True)
    proof={
      "checked_at":datetime.now(timezone.utc).isoformat(),
      "site":ROOT,"health_http":hcode,"status_http":scode,
      "database_binding_present":health.get("database_binding_present"),
      "database_state":status.get("database"),"stage":health.get("stage"),
      "heartbeat":status.get("scheduled_heartbeat"),
      "collector_state":status.get("automatic_collectors"),
      "source_states":[{k:x.get(k) for k in ("source","league","status","records")}
           for x in status.get("sources",[])],
      "paid_calls":health.get("paid_provider_calls"),
      "odds_d1_http":ocode,"odds_d1_status":odds.get("status"),
      "result":"incomplete"
    }
    errors=[]
    if ocode!=200 or odds.get("status")!="ok" or odds.get("config",{}).get("collection_enabled") is not False:
        errors.append("Odds D1 0002 schema or explicit no-spend gate is not ready")
    if hcode!=200 or health.get("service")!="dames-picks-staging" or health.get("stage")!="staging":
        errors.append("Cloudflare Worker health check not correct")
    if health.get("database_binding_present") is not True:
        errors.append("DB binding not deployed or not visible in Worker runtime")
    if health.get("paid_provider_calls")!="disabled" or health.get("provider_collection_active") is not False:
        errors.append("No-spend and no-provider-collection safeguards are not intact")
    if scode!=200 or status.get("database")!="connected":
        errors.append("D1 database cannot be queried; first migration not initialized or deploy not finished")
    if status.get("status") not in ("collectors_not_ready","data_ready"):
        errors.append("Unexpected database-readiness state: "+str(status.get("status")))
    sources=status.get("sources",[])
    expected={"nba_scores","nba_player_stats","nfl_scores","nfl_player_stats",
              "prizepicks_standard_lines","frozen_ai_projections","postgame_grades"}
    if set(x.get("source") for x in sources)!=expected:
        errors.append("Seven expected source-health records missing or duplicated")
    if status.get("automatic_collectors")!="not_connected":
        errors.append("Unexpected claim that live-data collectors are connected")
    heartbeat=status.get("scheduled_heartbeat")
    if not isinstance(heartbeat,dict):
        errors.append("No persisted Cloudflare Cron heartbeat observed")
    else:
        if heartbeat.get("job")!="staging-heartbeat" or heartbeat.get("outcome")!="success":
            errors.append("Persisted Cron heartbeat has invalid job or outcome")
        stamp=heartbeat.get("scheduled_at","")
        try: at=datetime.fromisoformat(stamp.replace("Z","+00:00"))
        except Exception: at=None
        if at is None or abs((datetime.now(timezone.utc)-at).total_seconds())>45*60:
            errors.append("Heartbeat is missing, out of date or in the future")
    proof["errors"]=errors
    proof["result"]="pass" if not errors else "incomplete"
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(proof,indent=2)+"\n")
    for error in errors:print("GATE:",error,flush=True)
    if errors:
        print("NOT COMPLETE: D1/Cron unverified. No sports source is being automatically refreshed.",flush=True)
        return 1
    print("PASS: live Cloudflare D1 binding, exact seven source rows, persistent Cron heartbeat; no paid sports/odds calls.",flush=True)
    print("LIMIT: actual player stats, lines, model inference and grading collectors NOT running.",flush=True)
    return 0

if __name__=="__main__":
    try:sys.exit(verify())
    except Exception as exc:
        print("LIVE PROBE BLOCKED:",type(exc).__name__,str(exc)[:300],file=sys.stderr,flush=True)
        sys.exit(2)

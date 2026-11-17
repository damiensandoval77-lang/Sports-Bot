#!/usr/bin/env python3
"""Read-only check of Cloudflare secret metadata across repeated HTTP fetches.
Never requests or logs any secret value; never contacts The Odds API.
"""
import json,time,urllib.request,urllib.error,sys
from datetime import datetime,timezone
ROOT="https://dames-picks-staging.damiensandoval77.workers.dev"
def get(path):
    req=urllib.request.Request(ROOT+path+"?probe="+str(time.time_ns()),headers={"User-Agent":"DamesPicks-Secret-Metadata-Consistency/1","Cache-Control":"no-cache"})
    try:
        with urllib.request.urlopen(req,timeout=16) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:
        return e.code,json.load(e)
def main():
    seen=[]
    for i in range(12):
        health_code,health=get("/healthz")
        status_code,status=get("/api/v1/odds/connection")
        record={
          "attempt":i+1,"health_http":health_code,"connection_http":status_code,
          "secret_configured":status.get("secret_configured"),
          "stored_status":status.get("status"),
          "auth_verified":status.get("key_authentication_verified"),
          "provider_http":status.get("http_status"),
          "last_call_credits":status.get("last_call_credits"),
          "probe_time":status.get("probe_time"),
          "quota_remaining":status.get("quota_remaining"),
          "paid_provider_calls":health.get("paid_provider_calls"),
          "worker_live":health.get("worker_reachable"),
        }
        print(json.dumps(record),flush=True);seen.append(record)
        if i<11:time.sleep(6)
    assert all(x["health_http"]==200 and x["connection_http"]==200 for x in seen)
    assert all(x["paid_provider_calls"]=="disabled" for x in seen)
    true=sum(x["secret_configured"] is True for x in seen)
    false=sum(x["secret_configured"] is False for x in seen)
    print("META_ONLY_COUNTS:",json.dumps({"secret_true":true,"secret_false":false,"total":len(seen)}),flush=True)
    if true and false:print("INCONSISTENT: secret available only in a subset of deployed HTTP Worker instances")
    elif true:print("CONSISTENT: secret now visible in every HTTP Worker sample")
    else:print("CONSISTENT: HTTP Worker still does not see secret, despite stored Cron authentication result")
    if not any(x["provider_http"]==200 and x["last_call_credits"]==0 for x in seen):
        print("WARNING: no verified 0-credit check in stored receipt")
if __name__=="__main__":main()

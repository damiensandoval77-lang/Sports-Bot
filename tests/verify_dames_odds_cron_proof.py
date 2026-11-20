#!/usr/bin/env python3
"""Read-only live evidence for zero-credit Odds API authentication from Cron.
Public endpoint only; no provider API calls, secrets or paid requests.
"""
import json,time,sys,urllib.request,urllib.error
BASE="https://dames-picks-staging.damiensandoval77.workers.dev"
def data(path):
  req=urllib.request.Request(BASE+path+"?qa="+str(time.time_ns()),headers={"Cache-Control":"no-store","User-Agent":"DamesPicks-CronReceiptVerifier/1"})
  with urllib.request.urlopen(req,timeout=17) as resp:return resp.status,json.load(resp)
def verify():
  last=None
  for i in range(24):
    try:
      code,auth=data("/api/v1/odds/connection")
      hc,health=data("/healthz")
      last={"http":code,"secret_http_visible":auth.get("http_handler_secret_visible"),
       "cron_authenticated":auth.get("scheduled_cron_authentication_verified"),
       "inconsistent":auth.get("http_cron_binding_mismatch"),
       "result":auth.get("status"),"source_status":auth.get("http_status"),
       "provider_credits_charged":auth.get("last_call_credits"),
       "provider_remaining":auth.get("quota_remaining"),
       "paid_calls":health.get("paid_provider_calls"),
       "probe_time":auth.get("probe_time")}
      print("PROBE",i+1,json.dumps(last,sort_keys=True),flush=True)
      if code==200 and hc==200 and health.get("service")=="dames-picks-staging" and \
          auth.get("scheduled_cron_authentication_verified") is True and \
          auth.get("key_authentication_verified") is True and \
          auth.get("http_status")==200 and auth.get("last_call_credits")==0 and \
          auth.get("status") in ("authenticated","authenticated_by_cron_http_binding_mismatch") and \
          health.get("paid_provider_calls")=="disabled":
        print("PASS: scheduled Cloudflare Worker authenticated key on free endpoint, charged zero credits; status distinguishes HTTP secret binding truth.",flush=True)
        return 0
    except Exception as e:print("Temporary worker deployment/HTTPS delay",str(e)[:100],flush=True)
    if i<23:time.sleep(12)
  print("FAIL: latest state",json.dumps(last),flush=True)
  return 1
if __name__=="__main__":sys.exit(verify())

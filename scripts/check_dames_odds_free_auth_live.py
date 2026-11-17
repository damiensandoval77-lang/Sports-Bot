#!/usr/bin/env python3
"""Read-only actual Cloudflare free credential check; no Odds API call here.
Cloudflare's scheduled handler performs the zero-credit /v4/sports request.
"""
import json
import sys
import time
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from pathlib import Path

ROOT="https://dames-picks-staging.damiensandoval77.workers.dev"
OUT=Path("test-artifacts/dames-odds-free-auth-live.json")

def fetch(path):
  req=Request(ROOT+path+"?audit="+str(int(time.time())),headers={
   "User-Agent":"DamesPicks-IndependentZeroCreditAudit/1","Cache-Control":"no-cache"})
  try:
    with urlopen(req,timeout=17) as response:
      return response.status,json.load(response)
  except HTTPError as error:
    try:return error.code,json.loads(error.read().decode("utf-8","replace"))
    except Exception:return error.code,{}

def verify():
  health_http,health=fetch("/healthz")
  auth_http,auth=fetch("/api/v1/odds/connection")
  budget_http,budget=fetch("/api/v1/odds/budget")
  payload={
    "verified_at":datetime.now(timezone.utc).isoformat(),
    "public_staging_url":ROOT,
    "health_http":health_http,"connection_http":auth_http,"budget_http":budget_http,
    "worker_service":health.get("service"),
    "database_binding_present":health.get("database_binding_present"),
    "paid_provider_calls":health.get("paid_provider_calls"),
    "provider_collection_configured":health.get("provider_collection_configured"),
    "secret_configured":auth.get("secret_configured"),
    "auth_state":auth.get("status"),
    "provider_http":auth.get("http_status"),
    "last_call_credits":auth.get("last_call_credits"),
    "quota_remaining":auth.get("quota_remaining"),
    "nba_active":auth.get("nba_active"),"nfl_active":auth.get("nfl_active"),
    "probe_time":auth.get("probe_time"),
    "model_or_paid_odds_collection_verified":False
  }
  # Never copy the complete upstream response, headers, request, or a secret.
  OUT.parent.mkdir(exist_ok=True,parents=True)
  OUT.write_text(json.dumps(payload,indent=2)+"\n")
  print("READ-ONLY CLOUDFLARE AUDIT:",json.dumps(payload,sort_keys=True),flush=True)
  if health_http!=200 or health.get("service")!="dames-picks-staging":
    return "blocker:worker_unavailable"
  if health.get("paid_provider_calls")!="disabled" or health.get("provider_collection_configured") is not False:
    return "blocker:paid_provider_guard"
  if budget_http!=200 or budget.get("config",{}).get("collection_enabled") is not False:
    return "blocker:budget_or_db"
  if auth_http!=200:
    return "pending:deployment"
  if auth.get("status")=="secret_not_configured" or auth.get("secret_configured") is False:
    return "blocker:cloudflare_secret_missing"
  if auth.get("status")=="authentication_rejected":
    return "blocker:invalid_odds_api_key"
  if auth.get("key_authentication_verified") is True and auth.get("last_call_credits")==0:
    return "pass:authenticated_zero_credits"
  return "pending:next_cloudflare_cron"
def main():
  state="pending:initial"
  for attempt in range(1,65):
    try:state=verify()
    except (URLError,TimeoutError,OSError,ValueError) as e:
      print("Transient HTTPS verifier failure",str(e)[:180]);state="pending:http_retry"
    print("STAGING FREE KEY RESULT",attempt,state,flush=True)
    if state.startswith("pass:"):return 0
    if state.startswith("blocker:"):return 1
    if attempt<64:time.sleep(15)
  return 1
if __name__=="__main__":sys.exit(main())

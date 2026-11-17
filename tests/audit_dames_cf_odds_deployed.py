#!/usr/bin/env python3
"""External read-only Cloudflare Odds API staging market audit, no provider calls.
Must not label a D1 setup failure as working sports automation.
"""
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime,timezone
ROOT="https://dames-picks-staging.damiensandoval77.workers.dev"

def get(path):
    request=urllib.request.Request(ROOT+path+("?_" if "?" not in path else "&_")+str(int(time.time())),
      headers={"Cache-Control":"no-cache","User-Agent":"DamesPicks-Odds-ReadOnlyDeploymentProbe/1"})
    try:
      with urllib.request.urlopen(request,timeout=18) as r:
       return r.status,r.read(500000).decode("utf-8","replace")
    except urllib.error.HTTPError as e:
      return e.code,e.read(500000).decode("utf-8","replace")

def probe():
    info={"checked_at":datetime.now(timezone.utc).isoformat(),"source":ROOT,
      "paid_provider_calls_made":0,"checks":[]}
    def check(name,result,details=""):
      info["checks"].append({"name":name,"pass":bool(result),"details":details})
      print(("PASS" if result else "FAIL")+": "+name+" "+str(details)[:180],flush=True)
    code,raw=get("/api/v1/odds/catalog")
    try:body=json.loads(raw)
    except Exception:body={}
    check("odds catalog deployed",code==200 and body.get("provider_use","").startswith("odds and prop lines"),
      str(code))
    markets=body.get("leagues",{})
    nba=[x.get("key") for x in markets.get("NBA",{}).get("markets",[])]
    nfl=[x.get("key") for x in markets.get("NFL",{}).get("markets",[])]
    check("NBA/NFL documented market coverage present",
      all(x in nba for x in ("player_points","player_assists","player_threes","player_turnovers")) and
      all(x in nfl for x in ("player_receptions","player_reception_yds","player_rush_yds")))
    check("alternates excluded",not any("_alternate" in str(x) for x in nba+nfl))

    code,raw=get("/healthz")
    try:health=json.loads(raw)
    except Exception:health={}
    check("Worker cost controls remain disabled",code==200 and health.get("service")=="dames-picks-staging"
      and health.get("paid_provider_calls")=="disabled" and health.get("provider_collection_configured") is False,
      {"status":code,"configured":health.get("provider_collection_configured")})
    code,raw=get("/api/v1/odds/budget")
    try:budget=json.loads(raw)
    except Exception:budget={}
    check("budget reports no paid collection",code in (200,503) and budget.get("config",{}).get("collection_enabled") is False,
      {"http":code,"state":budget.get("status")})

    for league in ("NBA","NFL"):
      code,raw=get("/api/v1/odds/board?league="+league)
      try:data=json.loads(raw)
      except Exception:data={}
      check(league+" market board serves only D1 or clear unavailable status",code in (200,503) and
        data.get("status") in ("available","no_recent_standard_lines","market_schema_unavailable","database_not_connected") and
        isinstance(data.get("quotes"),list),
        {"http":code,"status":data.get("status"),"rows":len(data.get("quotes",[]))})

    code,raw=get("/dames-picks/market-explorer.html")
    check("market explorer published",code==200 and "Market Explorer" in raw and
      "noindex,nofollow" in raw,str(code))
    code,raw=get("/dames-picks/market-explorer.js")
    check("market explorer interactive script published",code==200 and
      "No demo odds" in raw,str(code))
    code,raw=get("/dames-picks/")
    check("main design links to new markets",code==200 and "market-explorer.html" in raw,str(code))
    bad=[x for x in info["checks"] if not x["pass"]]
    print("VERDICT:",("PASS" if not bad else "FAIL"),"D1 sports collectors:",budget.get("status"),flush=True)
    return not bad
if __name__=="__main__":
    ok=False
    for i in range(18): # Allow Git-connected Cloudflare deployment to converge.
      try:ok=probe()
      except Exception as e:print("Probe not yet available:",str(e)[:300],flush=True)
      if ok:break
      if i<17:time.sleep(12)
    if not ok:sys.exit(1)

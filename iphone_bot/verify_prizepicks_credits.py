"""Single-request, secret-safe test of added PrizePicksAPI.com credits.

Never logs credentials, player information or response bodies. Uses the
existing GitHub Actions secret and a one-row NBA compact board request.
This is a provider-access test, not proof of full-slate coverage.
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

OUT=Path("docs/prizepicks_connection_health.json")
URL="https://prizepicksapi.com/api/v1/projections?league=NBA&view=compact&limit=1"

def probe():
    observed=dt.datetime.now(dt.timezone.utc).isoformat()
    key=os.environ.get("PRIZEPICKS_API_KEY","").strip()
    result={"checked_at":observed,"provider":"independent_prizepicksapi.com",
            "scope":"ONE_AUTHENTICATED_COMPACT_NBA_REQUEST",
            "full_slate_coverage_verified":False,
            "credentials_disclosed":False}
    if not key:
        result["status"]="GITHUB_SECRET_MISSING"
        return result
    request=urllib.request.Request(URL,headers={
        "Authorization":"Bearer "+key,"Accept":"application/json",
        "User-Agent":"Sports-Bot/PrizePicksAccessCheck"})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            data=json.load(response)
        result["status"]="API_ACCESS_CONFIRMED"
        result["response_is_json_object"]=isinstance(data,dict)
        result["returned_projection_count"]=len(data.get("data",[])) if isinstance(data,dict) and isinstance(data.get("data"),list) else None
        result["provider_mode"]=str(data.get("meta",{}).get("mode","unknown"))[:40] if isinstance(data,dict) and isinstance(data.get("meta"),dict) else "unknown"
    except urllib.error.HTTPError as error:
        result["status"]={401:"INVALID_KEY_OR_AUTH_FAILED",403:"FORBIDDEN_OR_PLAN_BLOCKED",
                           402:"PAYMENT_REQUIRED",429:"RATE_OR_MONTHLY_QUOTA_LIMITED"}.get(error.code,"HTTP_ERROR")
        result["http_status"]=error.code
    except Exception as error:
        result["status"]="REQUEST_FAILED"
        result["error_type"]=type(error).__name__
    return result

if __name__=="__main__":
    outcome=probe()
    OUT.write_text(json.dumps(outcome,indent=2)+"\n")
    print("PrizePicks access status:",outcome["status"],
          "http:",outcome.get("http_status"),"rows:",outcome.get("returned_projection_count"),
          "mode:",outcome.get("provider_mode"))

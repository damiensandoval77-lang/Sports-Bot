"""One small authenticated independent PrizePicks provider quota probe.

Does not page the slate or write any offers. The single compact NBA request
may consume a provider credit. Report the HTTP result and quota metadata only.
"""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/prizepicks_account_balance.json"
URL="https://prizepicksapi.com/api/v1/projections"

def check(key):
    result={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
            "provider":"independent_prizepicksapi.com",
            "request":"ONE_SMALL_COMPACT_NBA_PAGE_NO_STORED_OFFERS",
            "sportsbook_credits_spent":0,"raw_player_lines_published":False}
    if not key:return {**result,"status":"MISSING_API_KEY"}
    req=urllib.request.Request(URL+"?"+urllib.parse.urlencode({
          "league":"NBA","status":"active","view":"compact","limit":1}),
          headers={"Authorization":"Bearer "+key,"Accept":"application/json",
                   "X-User-Request":"Verify PrizePicks research provider quota"})
    try:
        with urllib.request.urlopen(req,timeout=18) as response:
            body=response.read(65537)
            if len(body)>65536:return {**result,"status":"RESPONSE_TOO_LARGE"}
            data=json.loads(body)
            def integer(header):
                try:return int(response.headers.get(header))
                except (TypeError,ValueError):return None
            return {**result,"status":"AUTHENTICATED_RESPONSE",
               "http_status":response.status,
               "provider_mode":(data.get("meta") or {}).get("mode") if isinstance(data,dict) else None,
               "credit_cost":integer("X-Credits-Cost"),
               "remaining_credits":integer("X-Credits-Remaining"),
               "usage_unit":str(response.headers.get("X-Usage-Unit") or "")[:40],
               "source_status":(data.get("meta") or {}).get("source_status") if isinstance(data,dict) else None}
    except urllib.error.HTTPError as e:
        return {**result,"status":"HTTP_ERROR","http_status":e.code}
    except (urllib.error.URLError,ValueError,TimeoutError,OSError) as e:
        return {**result,"status":"NETWORK_OR_RESPONSE_ERROR","error_type":type(e).__name__}

def main():
    result=check(os.environ.get("PRIZEPICKS_API_KEY","").strip())
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()

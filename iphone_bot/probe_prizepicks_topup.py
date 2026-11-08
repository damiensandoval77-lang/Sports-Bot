"""One bounded live PrizePicks read to verify account top-up access.

User independently confirmed their dashboard shows purchased top-up credits
after monthly allowance exhaustion. X-Credits-Remaining alone may therefore
be incomplete evidence about available top-ups. This NEVER turns on recurring
requests or bypasses HTTP 429. Does not print or store player names/props.
"""
import datetime as dt
import json,os
from pathlib import Path
import urllib.error,urllib.parse,urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/prizepicks_topup_probe.json"
ENDPOINT="https://prizepicksapi.com/api/v1/projections"
MAX_BYTES=256000

def probe(key):
    result={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "source":"independent_prizepicksapi.com",
        "purpose":"ONE_TIME_TOPUP_ACCESS_VALIDATION",
        "requested_rows":100,"raw_offers_published":False,
        "ongoing_polling_enabled":False,
        "topup_credits_amount_from_api":None}
    if not key:return {**result,"status":"NO_GITHUB_API_KEY"}
    req=urllib.request.Request(ENDPOINT+"?"+urllib.parse.urlencode({
        "league":"NBA","status":"active","view":"compact","limit":100}),
        headers={"Authorization":"Bearer "+key,"Accept":"application/json",
         "X-User-Request":"One-time authenticated NBA line access validation after user confirmed top-up credits"})
    try:
        with urllib.request.urlopen(req,timeout=18) as reply:
            raw=reply.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:
                return {**result,"status":"RESPONSE_EXCEEDED_DIAGNOSTIC_LIMIT"}
            obj=json.loads(raw)
            meta=obj.get("meta",{}) if isinstance(obj,dict) else {}
            def integer(name):
                try:return int(reply.headers.get(name))
                except (TypeError,ValueError):return None
            values=obj.get("data") if isinstance(obj,dict) else None
            return {**result,"status":"LIVE_READ_SUCCEEDED",
                "http_status":reply.status,"provider_mode":meta.get("mode"),
                "provider_source_status":meta.get("source_status"),
                "returned_rows":len(values) if isinstance(values,list) else None,
                "has_next_page":bool(meta.get("next_cursor")),
                "request_cost":integer("X-Credits-Cost"),
                "remaining_credits_header":integer("X-Credits-Remaining"),
                "usage_unit":str(reply.headers.get("X-Usage-Unit") or "")[:40],
                "account_topups_reported_by_user_not_verified_by_header":True}
    except urllib.error.HTTPError as err:
        return {**result,"status":"HTTP_ERROR",
                "http_status":err.code,"not_retried":True}
    except (urllib.error.URLError,TimeoutError,OSError,ValueError) as err:
        return {**result,"status":"NETWORK_OR_RESPONSE_ERROR",
                "error_type":type(err).__name__}

def main():
    result=probe(os.getenv("PRIZEPICKS_API_KEY","").strip())
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()

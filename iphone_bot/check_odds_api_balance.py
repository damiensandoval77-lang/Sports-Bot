"""Read The Odds API current quota using its NBA /events endpoint.

This check does not request per-game player props or publish credentials.
It only reports provider quota headers from the existing ODDS_API_KEY secret.
"""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/"docs/odds_account_balance.json"
URL="https://api.the-odds-api.com/v4/sports/basketball_nba/events"

def check(key):
    result={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
            "provider":"The Odds API","check":"NBA_EVENTS_QUOTA_HEADERS_ONLY",
            "paid_player_prop_requests":0,"key_exposed":False}
    if not key:
        return {**result,"status":"MISSING_API_KEY","remaining_credits":None}
    req=urllib.request.Request(URL+"?"+urllib.parse.urlencode({"apiKey":key}),
                               headers={"User-Agent":"Sports-Bot-Quota-Check/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=20) as response:
            data=response.read(4*1024*1024+1)
            if len(data)>4*1024*1024:raise ValueError("Oversized schedule response")
            events=json.loads(data)
            def safe_int(name):
                raw=response.headers.get(name)
                try:return int(raw) if raw is not None else None
                except (ValueError,TypeError):return None
            remaining=safe_int("x-requests-remaining")
            return {**result,"status":"LIVE_PROVIDER_BALANCE_CHECKED",
                "http_status":response.status,
                "remaining_credits":remaining,
                "used_credits":safe_int("x-requests-used"),
                "last_request_cost":safe_int("x-requests-last"),
                "provider_nba_events":len(events) if isinstance(events,list) else None,
                "balance_verified":remaining is not None}
    except urllib.error.HTTPError as error:
        return {**result,"status":"HTTP_ERROR","http_status":error.code,
                "remaining_credits":None}
    except (urllib.error.URLError,TimeoutError,OSError,ValueError) as error:
        return {**result,"status":"NETWORK_OR_SCHEMA_ERROR","error_type":type(error).__name__,
                "remaining_credits":None}

def main():
    result=check(os.getenv("ODDS_API_KEY","").strip())
    STATUS.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()

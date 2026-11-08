"""One-shot network reachability probe, not data ingestion.

Makes a single historical WOWY request. Records HTTP status and top-level
JSON keys ONLY. Never saves third-party stats, rate-limit-sensitive content,
player results, or redirects. This does not establish permitted model usage.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/pbpstats_access_status.json"
URL="https://api.pbpstats.com/get-wowy-stats/nba"
PARAMS={"Season":"2021-22","SeasonType":"Regular Season",
        "TeamId":"1610612744","Type":"Player",
        "0Exactly1OnFloor":"201939","1Exactly1OffFloor":"203110"}
def probe():
    result={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
            "endpoint_host":"api.pbpstats.com",
            "test_type":"PUBLIC_HISTORICAL_SCHEMA_CONNECTIVITY_ONLY",
            "automated_ingestion_enabled":False,
            "licensed_use_verified":False,
            "provider_data_saved":False}
    request=urllib.request.Request(
        URL+"?"+urllib.parse.urlencode(PARAMS),
        headers={"User-Agent":"SportsBot-Connectivity-Diagnostic/1.0",
                 "Accept":"application/json"})
    try:
        with urllib.request.urlopen(request,timeout=12) as response:
            status=response.status
            # Cap diagnostic response memory; never serialize payload itself.
            data=response.read(32768)
            result["http_status"]=status
            result["content_type"]=response.headers.get("Content-Type","").split(";")[0]
            try:
                parsed=json.loads(data)
                result["response_shape"]="OBJECT" if isinstance(parsed,dict) else (
                    "ARRAY" if isinstance(parsed,list) else "OTHER")
                if isinstance(parsed,dict):
                    result["top_level_keys"]=sorted(str(k) for k in parsed.keys())[:24]
                result["access_status"]="HTTP_SUCCESS"
            except (ValueError,UnicodeDecodeError):
                result["response_shape"]="UNCONFIRMED_OR_LARGE_JSON"
                result["access_status"]="HTTP_SUCCESS_RESPONSE_NOT_FULLY_PARSED"
    except urllib.error.HTTPError as exc:
        result["http_status"]=exc.code
        result["access_status"]="HTTP_ERROR"
    except (urllib.error.URLError,TimeoutError,OSError) as exc:
        result["access_status"]="NETWORK_ERROR"
        result["error_type"]=type(exc).__name__
    return result
def main():
    result=probe()
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()

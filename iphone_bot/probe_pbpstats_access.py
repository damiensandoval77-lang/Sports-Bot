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
MAX_RESPONSE_BYTES=8*1024*1024

def response_schema(payload):
    """Bounded field-names-only schema summary; never reveal player values."""
    if not isinstance(payload,dict):
        return {"response_shape":"ARRAY" if isinstance(payload,list) else "OTHER"}
    info={"response_shape":"OBJECT",
          "top_level_keys":sorted(str(k) for k in payload)[:30]}
    for table in ("multi_row_table_data","single_row_table_data","results"):
        value=payload.get(table)
        if isinstance(value,dict):
            info[table+"_shape"]="OBJECT"
            info[table+"_keys"]=sorted(str(k) for k in value)[:35]
            for item in value.values():
                if isinstance(item,list) and item and isinstance(item[0],dict):
                    info[table+"_nested_row_keys"]=sorted(str(k) for k in item[0])[:50]
                    break
        elif isinstance(value,list):
            info[table+"_shape"]="ARRAY"
            info[table+"_row_count"]=len(value)
            if value and isinstance(value[0],dict):
                names=sorted(str(k) for k in value[0])
                info[table+"_row_keys"]=names[:50]
                info[table+"_total_key_count"]=len(names)
                # Field names ONLY, never data values. These are the signals
                # needed to verify a real normalized WOWY importer mapping.
                wanted=("minutes","second","game","points","assists","rebound",
                        "poss","entity","player","fieldgoal","fga","fg2a","fg3a")
                info[table+"_relevant_keys"]=[
                    name for name in names if any(term in name.casefold()
                      for term in wanted)][:100]
            elif value and isinstance(value[0],list):
                info[table+"_row_type"]="ARRAY"
                info[table+"_row_width"]=len(value[0])
        elif value is not None:
            info[table+"_shape"]="OTHER"
    return info

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
            # Read one capped provider response IN MEMORY. Never write it to
            # the repository or emit player metrics in logs.
            data=response.read(MAX_RESPONSE_BYTES+1)
            result["http_status"]=status
            result["content_type"]=response.headers.get("Content-Type","").split(";")[0]
            result["response_bytes_read"]=len(data)
            if len(data)>MAX_RESPONSE_BYTES:
                result["access_status"]="HTTP_SUCCESS_TOO_LARGE_FOR_SCHEMA_PROBE"
                result["response_shape"]="LARGE_JSON_UNINSPECTED"
            else:
                try:
                    parsed=json.loads(data)
                    result.update(response_schema(parsed))
                    result["access_status"]="HTTP_SUCCESS"
                except (ValueError,UnicodeDecodeError):
                    result["response_shape"]="UNPARSEABLE_JSON"
                    result["access_status"]="HTTP_SUCCESS_RESPONSE_NOT_PARSED"
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

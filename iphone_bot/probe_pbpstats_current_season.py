"""Single-run 2026-27 WOWY query inspection; never capture third-party stats.

Tests API date-filter acceptance and whether both teammate-on and teammate-off
return the target EntityId. Does not store raw statistics or scrape in bulk.
Does not establish permission for ongoing prop-model use.
"""
import datetime as dt
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request
try:
    from .pbpstats_request_plan import request_plan
except ImportError:
    from pbpstats_request_plan import request_plan

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/pbpstats_current_season_probe.json"
MAX_RESPONSE=8*1024*1024

def shape(payload,target_id):
    if not isinstance(payload,dict):
        return {"response_shape":"INVALID"}
    rows=payload.get("multi_row_table_data")
    if not isinstance(rows,list):
        return {"response_shape":"NO_PLAYER_ROWS",
                "top_level_keys":sorted(str(x) for x in payload)[:15]}
    matched=[x for x in rows if isinstance(x,dict)
             and str(x.get("EntityId"))==str(target_id)]
    keys=sorted(matched[0]) if len(matched)==1 else []
    return {"response_shape":"PLAYER_ROWS",
            "row_count":len(rows),
            "target_entity_match_count":len(matched),
            "required_fields_present":{f:f in keys for f in
                ("EntityId","Points","Rebounds","Assists","Minutes","SecondsPlayed")},
            "game_date_fields_present":[k for k in keys if "date" in k.lower() or "gameid" in k.lower()]}

def one(endpoint,params,target):
    request=urllib.request.Request(
        endpoint+"?"+urllib.parse.urlencode(params),
        headers={"Accept":"application/json",
                 "User-Agent":"SportsBot-Research-OneShot-Diagnostic/1.0"})
    try:
        with urllib.request.urlopen(request,timeout=18) as response:
            buf=response.read(MAX_RESPONSE+1)
            summary={"http_status":response.status,
                     "content_type":response.headers.get("Content-Type","").split(";")[0]}
            if len(buf)>MAX_RESPONSE:
                return {**summary,"status":"RESPONSE_EXCEEDED_SAFE_LIMIT"}
            try:
                return {**summary,**shape(json.loads(buf),target),"status":"PARSED"}
            except (ValueError,UnicodeDecodeError):
                return {**summary,"status":"NON_JSON_OR_MALFORMED"}
    except urllib.error.HTTPError as error:
        return {"http_status":error.code,"status":"HTTP_ERROR"}
    except (urllib.error.URLError,OSError,TimeoutError) as error:
        return {"status":"NETWORK_ERROR","error_type":type(error).__name__}

def main():
    # Historical cutoff before November 7 NBA tipoffs, never current full season.
    plan=request_plan("201939","203110","GSW",cutoff_date="2026-11-06")
    output={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
            "season":"2026-27","cutoff":"2026-11-06",
            "provider":"PBP Stats","scope":"ONE_SHOT_NONPERSISTENT_METADATA_ONLY",
            "licensed_use_verified":False,
            "automated_live_ingestion_enabled":False,
            "source_stats_stored":False,
            "queries":{}}
    for kind in ("with","without"):
        output["queries"][kind]=one(plan["endpoint"],plan["requests"][kind],plan["player_id"])
    OUTPUT.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output,sort_keys=True))
if __name__=="__main__":
    main()

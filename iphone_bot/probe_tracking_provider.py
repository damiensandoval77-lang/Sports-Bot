"""Bounded metadata-only SportsQuanta tracking entitlement and schema probe.

No stats are printed or stored. Do not confuse season tracking aggregates with
game-dated potential assists and rebound chances; the pregame challenger
requires independent completed GAME IDs and observations. The probe only
runs network operations when explicitly invoked with a secret token.
"""
import json
import os
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/tracking_provider_access_status.json"
URL="https://api.sportquanta.com/v1/nba/player-tracking"
MAX_BYTES=2*1024*1024

def evaluate_schema(payload):
    data=payload.get("data") if isinstance(payload,dict) else None
    items=data.get("items") if isinstance(data,dict) else None
    if not isinstance(items,list):
        return {"schema":"NO_EXPECTED_ITEMS","tracked_players":0,
                "has_both_opportunity_fields":False,"has_dated_player_game_rows":False}
    both=0;dated=0
    for row in items:
        if not isinstance(row,dict):continue
        passing=row.get("passing");reb=row.get("rebounding")
        if (isinstance(passing,dict) and isinstance(reb,dict)
            and passing.get("potential_assists") is not None
            and reb.get("rebound_chances") is not None):both+=1
        if all(row.get(k) is not None for k in ("game_id","game_date",
                                                 "player_id","minutes")):dated+=1
    # This endpoint's documented response is an aggregate; even if it has
    # date-like metadata, it has not yet proven a complete game-level history.
    return {"schema":"SEASON_PLAYER_AGGREGATES","tracked_players":len(items),
        "players_with_both_fields":both,
        "has_both_opportunity_fields":both>0,
        "has_dated_player_game_rows":dated>0,
        "date_provenance_verified":False,
        "qualified_for_pregame_gamelevel_import":False}

def probe(token=None):
    result={"checked_at":datetime.now(timezone.utc).isoformat(),
      "provider":"SPORTQUANTA","endpoint":"NBA_PLAYER_TRACKING_SEASON",
      "gamelevel_tracking_connected":False,
      "licensed_use_verified":False,"raw_stats_published":False,
      "live_model_changed":False}
    token=token if token is not None else os.getenv("SPORTQUANTA_API_KEY")
    if not token:
        return {**result,"status":"NOT_CONFIGURED_NEEDS_PROVIDER_TOKEN"}
    req=urllib.request.Request(
      URL+"?"+urllib.parse.urlencode({"season":2026,"limit":500}),
      headers={"Authorization":"Bearer "+token,"Accept":"application/json",
               "User-Agent":"SportsBot-AuthorizedSchemaDiagnostic/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=15) as resp:
            raw=resp.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:return {**result,"status":"RESPONSE_TOO_LARGE"}
            if resp.status!=200:return {**result,"status":"UNEXPECTED_HTTP_STATUS",
                                        "http_status":resp.status}
            parsed=json.loads(raw)
            return {**result,"status":"HTTP_SUCCESS_AGGREGATE_ONLY",
                    "http_status":200,**evaluate_schema(parsed)}
    except urllib.error.HTTPError as e:
        return {**result,"status":"ACCESS_DENIED_OR_ENDPOINT_ERROR",
                "http_status":e.code}
    except (urllib.error.URLError,TimeoutError,OSError,ValueError) as e:
        return {**result,"status":"NETWORK_OR_RESPONSE_ERROR",
                "error_type":type(e).__name__}

def main():
    status=probe()
    OUT.write_text(json.dumps(status,indent=2)+"\n")
    print(json.dumps(status,sort_keys=True))

if __name__=="__main__":main()

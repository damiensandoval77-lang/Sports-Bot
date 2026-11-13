"""Secret-only NBA PrizePicks board collector (no Replit dependency).

Uses documented prizepicksapi.com REST v1. Never logs request URLs with keys,
never sends keys to browser code, and never silently treats a partial page as
complete coverage. Outputs a private CI artifact by default, NOT docs/.
"""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

BASE="https://prizepicksapi.com/api/v1/projections"
MAX_PAGES=2
REQUEST_CONTEXT="Sports-Bot NBA research board snapshot for personal analysis"

def select(row):
    """Minimize stored fields; no fabricated projections or pick directions."""
    if not isinstance(row,dict) or row.get("is_demo") is True:
        return None
    player=row.get("player") or {}
    event=row.get("event") or {}
    market=row.get("market") or {}
    sides=row.get("selections") or []
    if not isinstance(player,dict) or not isinstance(event,dict) or not isinstance(market,dict):
        return None
    if not isinstance(row.get("line"),(int,float)) or isinstance(row.get("line"),bool):
        return None
    if not row.get("id") or not player.get("name") or not event.get("starts_at"):
        return None
    return {
        "id":str(row["id"]), "player":player["name"], "player_id":str(player.get("id") or ""),
        "team":player.get("team"), "opponent":event.get("opponent"),
        "start":event.get("starts_at"), "stat":market.get("stat"),
        "period":market.get("period"), "line":row["line"],
        "selections":[{"side":s.get("side"),"tier":s.get("tier"),"available":s.get("available")}
                      for s in sides if isinstance(s,dict)],
        "observed_at":row.get("observed_at"),"status":row.get("status"),
        "source":"prizepicksapi.com / PrizePicks observation"
    }

def collect(fetch_page, max_pages=MAX_PAGES, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if max_pages<1 or max_pages>10:
        raise ValueError("max_pages must be 1..10")
    rows=[]; seen=set(); cursors=set();cursor=None;status=None;last_meta={}
    for page in range(max_pages):
        response=fetch_page(cursor)
        if not isinstance(response,dict) or not isinstance(response.get("data"),list):
            raise ValueError("Malformed API response")
        meta=response.get("meta") or {}
        if meta.get("mode")=="demo" or any(r.get("is_demo") for r in response["data"] if isinstance(r,dict)):
            raise ValueError("Demo response cannot be published as real lines")
        if meta.get("source_status") not in ("fresh","partial"):
            raise ValueError("API source not verified fresh or partial")
        status=meta["source_status"];last_meta=meta
        for r in response["data"]:
            s=select(r)
            if s is not None and s["id"] not in seen:
                seen.add(s["id"]);rows.append(s)
        cursor=meta.get("next_cursor")
        if cursor is None:
            return {"generated_at":now.isoformat(),"status":("VERIFIED_NBA_PRIZEPICKS_SNAPSHOT" if status=="fresh" else "PARTIAL_NBA_PRIZEPICKS_SNAPSHOT"),
                    "source_status":status,"complete_pagination":True,"pages":page+1,
                    "rows":rows,"line_source":"PrizePicks via prizepicksapi.com",
                    "is_ai_projection":False,"source_observed_at":meta.get("observed_at")}
        if not isinstance(cursor,str) or not cursor or cursor in cursors:
            raise ValueError("Invalid or repeated pagination cursor")
        cursors.add(cursor)
    return {"generated_at":now.isoformat(),"status":"PARTIAL_NBA_PRIZEPICKS_SNAPSHOT",
            "source_status":status,"complete_pagination":False,"pages":max_pages,
            "rows":rows,"line_source":"PrizePicks via prizepicksapi.com",
            "is_ai_projection":False,"source_observed_at":last_meta.get("observed_at")}

def main():
    api_key=os.environ.get("PRIZEPICKS_API_KEY","").strip()
    if not api_key:
        raise SystemExit("PRIZEPICKS_API_KEY missing: no paid request sent")
    max_pages=int(os.environ.get("PP_MAX_PAGES","1"))
    def fetch(cursor):
        args={"league":"NBA","limit":"200","status":"active"}
        if cursor:args["cursor"]=cursor
        url=BASE+"?"+urllib.parse.urlencode(args)
        req=urllib.request.Request(url,headers={
            "Authorization":"Bearer "+api_key,
            "Accept":"application/json",
            "X-User-Request":REQUEST_CONTEXT,
            "User-Agent":"Sports-Bot/1.0"
        })
        try:
            with urllib.request.urlopen(req,timeout=30) as rsp:
                return json.load(rsp)
        except urllib.error.HTTPError as err:
            # Do not echo response body or secret; quota/auth failures are not success.
            raise RuntimeError("PrizePicks provider HTTP "+str(err.code)) from None
    try:
        result=collect(fetch,max_pages=max_pages)
    except (RuntimeError,ValueError,urllib.error.URLError,TimeoutError) as err:
        raise SystemExit("PrizePicks collection failed: "+type(err).__name__) from None
    output=Path(os.environ.get("PP_OUTPUT","/tmp/sports_bot_prizepicks_snapshot.json"))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n")
    print("PrizePicks snapshot captured:",result["status"],
          "rows:",len(result["rows"]),"pages:",result["pages"],
          "complete:",result["complete_pagination"])
    # Partial snapshots are retained for diagnostics, not silently treated as full slate.
    if not result["complete_pagination"] or result["source_status"]!="fresh":
        raise SystemExit(2)

if __name__=="__main__":
    main()

"""Single 3-row authenticated compact schema check. No user key or names logged."""
import os,json,urllib.request,datetime
from pathlib import Path
URL="https://prizepicksapi.com/api/v1/projections?league=NBA&view=compact&status=active&limit=3"
req=urllib.request.Request(URL,headers={"Authorization":"Bearer "+os.environ["PRIZEPICKS_API_KEY"],
 "Accept":"application/json","X-User-Request":"Validate compact NBA prop schema for Sports-Bot"})
with urllib.request.urlopen(req,timeout=25) as f:
 data=json.load(f)
 meta=data.get("meta",{})
 rows=data.get("data",[])
def shape(row):
 if not isinstance(row,dict):return {"data_type":type(row).__name__}
 return {"keys":sorted(row),
   "types":{k:type(v).__name__ for k,v in row.items()},
   "non_identifying_fields":{k:row.get(k) for k in
      ("league","stat","period","status","is_demo","more_available",
       "less_available","more_tier","less_tier","event_starts_at")
       if k in row},
   "market_keys":sorted(row["market"]) if isinstance(row.get("market"),dict) else None,
   "event_keys":sorted(row["event"]) if isinstance(row.get("event"),dict) else None,
   "player_keys":sorted(row["player"]) if isinstance(row.get("player"),dict) else None,
   "selection_fields":sorted(row["selections"][0]) if isinstance(row.get("selections"),list)
      and row["selections"] and isinstance(row["selections"][0],dict) else None}
out={"checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "status":"COMPACT_SHAPE_INSPECTED",
 "meta_mode":meta.get("mode"),
 "meta_source_status":meta.get("source_status"),
 "first_three_shapes":[shape(r) for r in rows[:3]],
 "rows_returned":len(rows),
 "no_player_names_or_credentials_saved":True}
Path("docs/prizepicks_compact_schema.json").write_text(json.dumps(out,indent=2)+"\n")
print("Compact row structure inspected:",json.dumps(out,ensure_ascii=False)[:3400])

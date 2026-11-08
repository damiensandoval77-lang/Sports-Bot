"""Bounded schema probe for sportsdataverse public 2026-27 NBA schedules."""
import io,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
URL="https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/nba/schedules/parquet/nba_schedule_2027.parquet"
OUT=Path("docs/nba_external_schedule_probe.json")
def main():
 data={"checked_at":datetime.now(timezone.utc).isoformat(),
       "provider":"sportsdataverse/hoopR-nba-data",
       "url":URL,"status":"UNAVAILABLE"}
 try:
  req=urllib.request.Request(URL,headers={"User-Agent":"SportsBot-Schedule-Research/1.0"})
  with urllib.request.urlopen(req,timeout=25) as r:
   raw=r.read(8_000_001)
  if len(raw)>8_000_000:raise ValueError("Oversized schedule")
  frame=pd.read_parquet(io.BytesIO(raw))
  data.update(status="SCHEMA_INSPECTED",rows=len(frame),
    columns=list(map(str,frame.columns)),bytes=len(raw))
  candidates=[x for x in frame.columns if
      any(k in str(x).lower() for k in ("game_date","home_","away_","status"))]
  useful=[c for c in ("date","start_date","game_date_time","game_date",
      "home_display_name","away_display_name","home_abbreviation",
      "away_abbreviation","status_type_state","season_type")
      if c in frame.columns]
  data["preview"]=frame[useful].head(2).astype(str).to_dict(orient="records")
  data["november_8_preview"]=frame[frame["game_date"].astype(str).str.startswith("2026-11-08")][useful].head(3).astype(str).to_dict(orient="records")
 except (OSError,ValueError,TypeError,Exception) as e:
  data["error_type"]=type(e).__name__
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(data,indent=2)+"\n")
 print("External schedule schema:",data["status"],"rows:",data.get("rows",0),
       "columns:",data.get("columns",[]))
if __name__=="__main__":main()

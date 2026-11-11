"""Immutable longitudinal archive of actual pretip matchup-probability forecasts.

Never reconstruct a prediction after the game. Each observation links the
original *real* frozen standard line, side, opponent, game and model capture.
Append-only by unique forecast identity; on conflict reject rather than rewrite.
"""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from research.publish_matchup_shadow_guard import validate

STATUS="IMMUTABLE_PROSPECTIVE_MATCHUP_FORECAST_ARCHIVE"
def identity(x):
    return tuple(str(x.get(k) or "") for k in
      ("player_id","team","opponent","stat","start","line","original_side","captured_at"))
def add(archive,shadow):
    validate(shadow)
    if archive is None:
        archive={"status":STATUS,"version":1,"forecasts":[]}
    if archive.get("status")!=STATUS or archive.get("version")!=1 or not isinstance(archive.get("forecasts"),list):
        raise ValueError("bad historic archive")
    saved={}
    for row in archive["forecasts"]:
        k=identity(row)
        if not all(k) or k in saved:raise ValueError("duplicate or incomplete prior immutable forecast")
        saved[k]=row
    fresh=0
    for raw in shadow["records"]:
        item={**raw,"research_snapshot_captured_at":shadow["captured_at"],
             "source_run_id":shadow.get("model_id"),
             "observed_as_prospective":True}
        k=identity(item)
        if not all(k):raise ValueError("incomplete prospective identity")
        if k in saved:
            # No later workflow can tamper with an existing recorded forecast.
            if saved[k]!=item:raise ValueError("conflicting prior prospective forecast")
            continue
        saved[k]=item
        fresh+=1
    return {**archive,"forecasts":[saved[k] for k in sorted(saved)]},fresh
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--incoming",required=True)
    ap.add_argument("--current",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    shadow=json.loads(Path(a.incoming).read_text())
    path=Path(a.current)
    old=json.loads(path.read_text()) if path.exists() else None
    archive,new=add(old,shadow)
    Path(a.output).write_text(json.dumps(archive,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":STATUS,"added":new,"total":len(archive["forecasts"])}))
if __name__=="__main__":main()

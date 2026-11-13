"""Import an authorized per-game passing/rebounding tracking CSV privately.

No NBA.com calls. License permissions are human verified separately. Never
commit the source CSV or resulting normalized rows.
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path
from .tracking_opportunities_v1 import num
from .paper_pick_pipeline import utc

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/"data/nba/private/tracking_opportunities.json"
COLUMNS=("player_id","team","game_id","game_date","observed_at",
         "minutes","potential_assists","assists","rebound_chances","rebounds")

def normalize(rows,manifest):
    if not isinstance(manifest,dict):
        raise ValueError("Missing authorized provider manifest")
    required={"allowed_use":"NBA_PROP_RESEARCH",
              "reviewer_confirmation":"MANUALLY_VERIFIED"}
    if any(manifest.get(k)!=v for k,v in required.items()) or not str(manifest.get("permission_reference","")).strip():
        raise ValueError("Source rights for NBA prop research not verified")
    if manifest.get("season")!="2026-27" or not str(manifest.get("source","")).strip():
        raise ValueError("Missing provider source or correct season")
    try:issued=utc(manifest["generated_at"])
    except (KeyError,TypeError,ValueError):
        raise ValueError("Invalid generated_at timestamp")
    seen=set();output=[]
    for i,r in enumerate(rows):
        if not isinstance(r,dict) or any(k not in r for k in COLUMNS):
            raise ValueError(f"Tracking row {i} missing required fields")
        pid=str(r["player_id"]);gid=str(r["game_id"]);team=str(r["team"])
        if not pid.isdecimal() or not gid.isdecimal() or len(gid)!=10 or len(team)!=3:
            raise ValueError(f"Tracking row {i} invalid identity")
        try:
            date.fromisoformat(r["game_date"])
            when=utc(r["observed_at"])
            if when>issued or date.fromisoformat(r["game_date"])>when.date():
                raise ValueError("source timestamp precedes played game")
        except (KeyError,ValueError,TypeError):
            raise ValueError(f"Tracking row {i} invalid observation time")
        nums={x:num(r[x]) for x in ("minutes","potential_assists","assists","rebound_chances","rebounds")}
        if (any(x is None for x in nums.values()) or not 5<=nums["minutes"]<=60 or
            nums["assists"]>nums["potential_assists"] or
            nums["rebounds"]>nums["rebound_chances"]):
            raise ValueError(f"Tracking row {i} invalid chance counts or minutes")
        k=(pid,gid)
        if k in seen:raise ValueError("Duplicate player game tracking data")
        seen.add(k)
        output.append({**{x:r[x] for x in COLUMNS if x not in nums},**nums})
    if not output:raise ValueError("No real game tracking records supplied")
    return {"status":"AUTHORIZED_TRACKING_RESEARCH",
      "licensed_use_verified":True,"season":"2026-27",
      "source":manifest["source"],"generated_at":issued.isoformat(),
      "authorization":{k:manifest[k] for k in ("allowed_use",
         "reviewer_confirmation","permission_reference")},
      "observations":output}

def main(argv=None):
    parser=argparse.ArgumentParser(description="Normalize authorized tracking CSV to gitignored private data")
    parser.add_argument("--csv",type=Path,required=True)
    parser.add_argument("--authorization",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=PRIVATE)
    args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((ROOT/"data/nba/private").resolve()):
        parser.error("Tracking feed must stay in gitignored private directory")
    try:
        with args.csv.open(newline="") as fp:
            normalized=normalize(csv.DictReader(fp),json.loads(args.authorization.read_text()))
    except (OSError,ValueError,json.JSONDecodeError) as e:
        parser.error(str(e))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(normalized,indent=2)+"\n")
    print("Validated private tracking games:",len(normalized["observations"]),
          "No API calls and no public licensed game rows")

if __name__=="__main__":main()

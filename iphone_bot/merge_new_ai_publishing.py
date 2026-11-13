"""Conflict-safe publication of independent New AI frozen market records.

Fresh runner artifacts must NEVER replace main's newer grades or snapshots.
A saved pretip line and projection are immutable. Grades only use verified
NBA/ESPN final-player ledger, never live totals or implied probabilities.
"""
import argparse
import json
from pathlib import Path
from iphone_bot.multimarket_forecast_ledger import merge, key, valid, with_voids, utc

IMMUTABLE=("player_id","player","team","game","start","stat",
           "line","projection","market_updated","captured_at","pickem_tier",
           "standard_line_two_sided_verified")

def durable_merge(current,incoming,finals):
    if current and current.get("status")!="FROZEN_NEW_AI_ALL_MARKET":
        raise ValueError("Current frozen ledger status invalid")
    if incoming.get("status")!="FROZEN_NEW_AI_ALL_MARKET":
        raise ValueError("Incoming frozen ledger status invalid")
    old={}
    for r in current.get("records",[]):
        if not valid(r):
            raise ValueError("Invalid existing original pretip record")
        if key(r) in old and old[key(r)]!=r:
            raise ValueError("Conflicting existing frozen records")
        old[key(r)]=r
    runner={}
    for r in incoming.get("records",[]):
        if not valid(r):
            raise ValueError("Invalid runner original pretip record")
        if key(r) in runner and runner[key(r)]!=r:
            raise ValueError("Conflicting runner frozen records")
        runner[key(r)]=r
    concurrent=[]
    for ident,r in runner.items():
        prev=old.get(ident)
        if prev is not None and any(prev.get(f)!=r.get(f) for f in IMMUTABLE):
            # Two runners can independently freeze a newly observed threshold
            # before either sees the other's commit. Keep the already-published
            # original byte-for-byte; a distinct valid pending observation is
            # not permission to reprice, reproject, or revert its grade.
            if (r.get("grade")=="PENDING" and
                utc(prev["captured_at"]) != utc(r["captured_at"])):
                concurrent.append({"identity":list(ident),
                    "preserved_capture":prev["captured_at"],
                    "ignored_capture":r["captured_at"]})
                continue
            raise ValueError("Original frozen pretip market changed: "+str(ident))
        if prev and prev.get("grade") in ("GRADED","EXCLUDED_VERIFIED_DNP") and r.get("grade") in ("GRADED","EXCLUDED_VERIFIED_DNP"):
            if any(prev.get(k)!=r.get(k) for k in
                   ("grade","actual","final_source","source_game_id","absolute_error","direction_hit","verified_dnp_reason")):
                raise ValueError("Conflicting verified final grades: "+str(ident))
    # Feed form only adds previously absent, originally timestamped records.
    result=merge(current,{"status":"LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED",
                          "predictions":list(runner.values())},finals)
    for ident,prev in old.items():
        after=next((x for x in result["records"] if key(x)==ident),None)
        if after is None or any(after.get(f)!=prev.get(f) for f in IMMUTABLE):
            raise ValueError("Frozen pregame record disappeared or changed")
        if prev.get("grade") in ("GRADED","EXCLUDED_VERIFIED_DNP") and after.get("grade")!=prev.get("grade"):
            raise ValueError("Previously settled record reverted or changed status")
    result["concurrent_refreezes_ignored"]=concurrent
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--current",required=True)
    parser.add_argument("--incoming",required=True)
    parser.add_argument("--finals",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    def load(path):
        f=Path(path)
        return json.loads(f.read_text()) if f.exists() else {}
    result=durable_merge(load(args.current),load(args.incoming),with_voids(load(args.finals),Path(args.finals).with_name("espn_injury_void_ledger.json")))
    dest=Path(args.output)
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("DURABLE NEW AI RECORDS",len(result["records"]),"NEW",result["new_pregame_frozen"],
          "GRADED",sum(x.get("grade")=="GRADED" for x in result["records"]))
if __name__=="__main__":main()

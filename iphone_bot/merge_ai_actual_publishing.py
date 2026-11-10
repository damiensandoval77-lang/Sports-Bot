"""Fail-closed merge for published NBA AI-only verified final outcomes.

Do not replace existing source-verified outcomes or discard newly verified
grades because an older record exists under the same forecast identity.
"""
import json
from pathlib import Path

KEY=("player_id","team","game","start","stat")
IMMUTABLE=("player_id","player","team","game","start","stat","captured_at","projection","line")
RESOLVED={"GRADED","EXCLUDED_VERIFIED_DNP","EXCLUDED_VERIFIED_NONPARTICIPANT"}
FINAL_FIELDS=("status","actual","error","absolute_error","final_source",
              "source_game_id","minutes","verified_dnp_reason",
              "verified_nonparticipation_reason")

def key(row):
    return tuple(str(row.get(field) or "") for field in KEY)

def merge(current,incoming):
    result={}
    for source,records in (("current",current.get("records",[])),
                           ("incoming",incoming.get("records",[]))):
        for row in records:
            if not isinstance(row,dict) or not all(key(row)):
                raise ValueError("Invalid "+source+" AI grade identity")
            status=row.get("status")
            if status not in RESOLVED|{"PENDING"}:
                raise ValueError("Unknown "+source+" AI outcome status: "+str(status))
            ident=key(row)
            old=result.get(ident)
            if old is None:
                result[ident]=dict(row)
                continue
            if any(old.get(f)!=row.get(f) for f in IMMUTABLE):
                raise ValueError("Conflicting frozen forecast: "+str(ident))
            old_resolved=old.get("status") in RESOLVED
            incoming_resolved=status in RESOLVED
            if old_resolved and incoming_resolved:
                if any(old.get(f)!=row.get(f) for f in FINAL_FIELDS):
                    raise ValueError("Conflicting verified final AI outcome: "+str(ident))
                continue
            if incoming_resolved and not old_resolved:
                result[ident]=dict(row)  # only allowed forward state promotion
            # otherwise retain old record; never change verified final to pending
    ordered=sorted(result.values(),key=lambda r:(r.get("start",""),
                  r.get("game",""),r.get("player_id",""),r.get("stat","")))
    return {"version":1,"records":ordered}

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--current",required=True)
    parser.add_argument("--incoming",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    a=json.loads(Path(args.current).read_text())
    b=json.loads(Path(args.incoming).read_text())
    out=merge(a,b)
    Path(args.output).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print("NBA AI VERIFIED OUTCOME MERGE",len(out["records"]),"records",
          sum(r["status"]=="GRADED" for r in out["records"]),"graded")
if __name__=="__main__":main()

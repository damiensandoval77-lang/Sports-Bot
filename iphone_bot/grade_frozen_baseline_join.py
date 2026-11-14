"""Grade prospective pretip baseline/PrizePicks joins only from verified NBA/ESPN finals.

The original snapshot is NEVER edited. A baseline projection is not the
separate New AI simulator and a quote is not evidence of a placed bet.
"""
import datetime as dt
import json
import math
from pathlib import Path
from iphone_bot.reconcile_grading_production import observed_final

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/frozen_baseline_pregame_lines_2026-11-09.json"
ACTUAL=ROOT/"docs/ai_forecast_actual_ledger.json"
OUT=ROOT/"docs/frozen_baseline_pregame_lines_2026-11-09_grades.json"
ALLOWED={"NBA_CDN_FINAL","ESPN_FINAL"}
EXCLUSIONS={"EXCLUDED_VERIFIED_DNP","EXCLUDED_VERIFIED_NONPARTICIPANT"}

def instant(value):
    try:
        t=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return t if t.tzinfo and t.utcoffset() is not None else None
    except (TypeError,ValueError,OverflowError):return None

def ident(row):
    return tuple(str(row.get(k) or "") for k in ("player_id","team","game","start","stat"))

def grade(snapshot,finals):
    if snapshot.get("status") not in {"FROZEN_BASELINE_PRETIP_PP_LINES_FOR_RESEARCH","FROZEN_BASELINE_PRETIP_MARKETS_APPEND_ONLY"} or snapshot.get("immutable_predictions") is not True:
        raise ValueError("Original baseline snapshot absent/invalid")
    results=finals.get("records",[])
    index={}
    for f in results:
        if f.get("status") not in {"GRADED",*EXCLUSIONS}:continue
        if not observed_final(f):continue
        k=ident(f)
        if k in index and index[k]!=f:index[k]=None
        else:index.setdefault(k,f)
    seen=set()
    rows=[]
    for r in snapshot.get("records",[]):
        if not isinstance(r,dict) or r.get("source_model")!="PRETIP_AI_ONLY_ARCHIVE_BASELINE" or r.get("quote_tier")!="standard" or r.get("not_a_wager") is not True:
            raise ValueError("Unverified original snapshot record")
        k=ident(r)
        if k in seen:raise ValueError("Repeated frozen record identity")
        seen.add(k)
        start,locked,original,observed,generated=map(instant,(r.get("start"),r.get("locked_at"),r.get("model_captured_at"),r.get("quote_observed_at"),r.get("provider_snapshot_at")))
        if not all((start,locked,original,observed,generated)) or not (original<=locked<start and observed<=generated<=locked) or not isinstance(r.get("provider_quote_id"),str):
            raise ValueError("Original prediction or line not frozen prior to tipoff")
        value=r.get("line");projection=r.get("model_projection")
        if type(value) not in (int,float) or type(projection) not in (int,float) or not all(math.isfinite(float(v)) and 0<=v<=200 for v in (value,projection)):
            raise ValueError("Invalid authentic line/model projection")
        f=index.get(k)
        status="PENDING_VERIFIED_FINAL"
        actual=None;model_hit=None;difference=None;final_source=None;source_game_id=None
        if f and f.get("status") in EXCLUSIONS and f.get("final_source"):
            status=f["status"]
            final_source=f["final_source"]
            source_game_id=f["source_game_id"]
        elif f and f.get("status")=="GRADED":
            x=f.get("actual")
            if type(x) in (int,float) and math.isfinite(float(x)) and 0<=x<=250:
                actual=x;difference=round(abs(float(x)-float(projection)),4)
                model_hit=(x>value) if r.get("modeled_direction")=="More" else (x<value) if r.get("modeled_direction")=="Less" else None
                if x==value:status="VERIFIED_PUSH";model_hit=None
                else:status="GRADED_BASELINE_RESEARCH_ONLY"
                final_source=f.get("final_source");source_game_id=f.get("source_game_id")
        rows.append({**r,"grade_status":status,"verified_actual":actual,
                     "absolute_projection_error":difference,
                     "model_direction_hit":model_hit,
                     "verified_final_source":final_source,
                     "verified_source_game_id":source_game_id})
    return {"status":"BASELINE_PRETIP_PROSPECTIVE_GRADING",
        "game_date_eastern":snapshot.get("game_date_eastern"),
        "original_frozen_at":snapshot.get("captured_at") or snapshot.get("updated_at"),
        "total_original_records":len(rows),
        "verified_final_grades":sum(x["grade_status"]=="GRADED_BASELINE_RESEARCH_ONLY" for x in rows),
        "pushes":sum(x["grade_status"]=="VERIFIED_PUSH" for x in rows),
        "verified_exclusions":sum(x["grade_status"] in EXCLUSIONS for x in rows),
        "pending":sum(x["grade_status"]=="PENDING_VERIFIED_FINAL" for x in rows),
        "not_betting_roi":True,"records":rows}

def main():
    result=grade(json.loads(SOURCE.read_text()),json.loads(ACTUAL.read_text()))
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("FROZEN BASELINE GRADES",result["verified_final_grades"],"PENDING",result["pending"])
if __name__=="__main__":main()

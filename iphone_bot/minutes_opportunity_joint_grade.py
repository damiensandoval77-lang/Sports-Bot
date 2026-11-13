"""Grade jointly frozen Minutes V3 and AST/REB Opportunity V2 on exact settled props.

The already frozen original Combined AI quote and stat are immutable.
No opponent/injury hindsight. No reconstructed unrecorded new forecast.
"""
import json,math
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
try:
 from .paper_pick_pipeline import utc
except ImportError:
 from paper_pick_pipeline import utc
from statistics import mean
try:
 from .model_performance import independent_rows
except ImportError:
 from model_performance import independent_rows
ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"docs/minutes_v3_opportunity_v2_prospective.json"
def valid(x):
 if x is None or isinstance(x,bool):return None
 try:
  y=float(x)
  return y if math.isfinite(y) and y>=0 else None
 except (TypeError,ValueError):return None
def grade(records):
 pairs={"MIN":[],"AST":[],"REB":[]}
 missing={"NO_FROZEN_JOINT_RESEARCH":0,"NO_COMPLETED_RESULT":0,"UNSAFE_FEATURE_DATE":0}
 for r in independent_rows(records):
  market=r.get("market")
  if market not in ("AST","REB"):continue
  minutes=r.get("minutes_v3_research")
  op=r.get("opportunity_v2_research")
  stat=(op.get("markets") or {}).get(market,{}) if isinstance(op,dict) else {}
  if not isinstance(minutes,dict) or not stat or stat.get("status")!="PREGAME_OPPORTUNITY_V2_RESEARCH":
   missing["NO_FROZEN_JOINT_RESEARCH"]+=1;continue
  date=utc(r["event_start"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
  if (minutes.get("last_prior_date") or "9999")>=date or (stat.get("last_prior_game") or "9999")>=date:
   missing["UNSAFE_FEATURE_DATE"]+=1;continue
  baseline=valid(r.get("combined_projection"))
  actual=valid(r.get("actual"));line=valid(r.get("line"))
  challenge=valid(stat.get("projection"))
  original_minutes=valid((r.get("frozen_minutes_v2_research") or {}).get("expected_minutes"))
  new_minutes=valid(minutes.get("expected_minutes"))
  played=valid(r.get("actual_minutes"))
  if None in (baseline,actual,line,challenge,original_minutes,new_minutes,played):
   missing["NO_COMPLETED_RESULT"]+=1;continue
  pairs[market].append({"date":date,"actual":actual,"line":line,
      "baseline":baseline,"candidate":challenge,
      "source_kind":stat.get("source_kind")})
  pairs["MIN"].append({"date":date,"actual":played,
      "baseline":original_minutes,"candidate":new_minutes})
 def summarize(rows):
  n=len(rows)
  if not n:return {"paired":0,"distinct_game_dates":0,"baseline_mae":None,
                    "candidate_mae":None,"wins":None,"baseline_wins":None}
  out={"paired":n,"distinct_game_dates":len(set(v["date"] for v in rows)),
       "baseline_mae":round(mean(abs(v["actual"]-v["baseline"]) for v in rows),4),
       "candidate_mae":round(mean(abs(v["actual"]-v["candidate"]) for v in rows),4)}
  if "line" in rows[0]:
   eligible=[v for v in rows if v["actual"]!=v["line"] and
              v["baseline"]!=v["line"] and v["candidate"]!=v["line"]]
   out["paired_direction_grades"]=len(eligible)
   out["wins"]=sum((v["candidate"]>v["line"])==(v["actual"]>v["line"]) for v in eligible)
   out["baseline_wins"]=sum((v["baseline"]>v["line"])==(v["actual"]>v["line"]) for v in eligible)
   out["source_kind_counts"]={k:sum(v.get("source_kind")==k for v in rows)
         for k in sorted({v.get("source_kind") for v in rows})}
  return out
 return {"status":"FROZEN_JOINT_MINUTES_OPPORTUNITY_RESEARCH_GRADING",
    "updated_at":datetime.now(timezone.utc).isoformat(),
    "markets":{s:summarize(pairs[s]) for s in ("MIN","AST","REB")},
    "missing":missing,"production_applied":False,
    "prospective_minimum_distinct_dates":10,
    "verified_accuracy_gain":False,
    "notice":"Only original pretip frozen snapshots graded; empty until new eligible player markets settle."}
def main():
 data=json.loads(LEDGER.read_text())
 report=grade(data.get("records",[]))
 OUT.write_text(json.dumps(report,indent=2)+"\n")
 print("JOINT_FROZEN_GRADES",json.dumps(report["markets"]))
if __name__=="__main__":main()

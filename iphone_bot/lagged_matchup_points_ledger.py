"""Immutable first pre-tip capture and independently verified points grading.

Preserves distinct new-model history without rewriting legacy Combined AI,
its paper record or market quotes. The model-versus-line direction is a
descriptive retrospective test, not a validated betting recommendation.
"""
import json,math
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LIVE=ROOT/"docs/lagged_matchup_live_points.json"
LEDGER=ROOT/"docs/lagged_matchup_points_ledger.json"
FINAL=ROOT/"docs/ai_forecast_actual_ledger.json"
FINAL_SOURCES={"NBA_CDN_FINAL","ESPN_FINAL"}

def utc(value):
    try:
        t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if t.tzinfo is None or t.utcoffset() is None:raise ValueError
        return t.astimezone(timezone.utc)
    except (TypeError,ValueError) as e:raise ValueError("Timestamp invalid") from e

def identity(row):
    return "|".join(str(row.get(k) or "") for k in ("player_id","team","game","start","stat"))

def valid(row):
    if not isinstance(row,dict) or row.get("stat")!="PTS" or row.get("real_prizepicks_line") is not True:
        return False
    if not row.get("player_id") or not row.get("team") or not row.get("game"):
        return False
    if row.get("research_only") is not True or row.get("calibrated_probability") is not None:
        return False
    try:
        start=utc(row["start"]);captured=utc(row["captured_at"])
        quoted=utc(row["market_updated"])
        p=float(row["projection"]);line=float(row["line"])
        return (captured<start and quoted<=captured and quoted<start and
                all(math.isfinite(x) for x in (p,line)) and
                0<=p<=100 and 0<=line<=100)
    except (KeyError,TypeError,ValueError):
        return False

def update(previous,feed,finals):
    old=previous.get("records",[]) if previous.get("status")=="IMMUTABLE_PREGAME_NEW_MODEL_POINTS" else []
    frozen={}
    for x in old:
        if valid(x):
            k=identity(x)
            if k in frozen:
                # A true duplicate identity with conflicting earliest snapshot
                # cannot be safely rewritten.
                if frozen[k]!=x:raise ValueError("Conflicting historical snapshots")
            else:frozen[k]=dict(x)
    added=0
    if feed.get("status")=="LIVE_POINTS_CHALLENGER_UNCALIBRATED":
        for x in sorted(feed.get("predictions",[]),
                        key=lambda v:(v.get("captured_at",""),v.get("player_id",""),str(v.get("line","")))):
            if not valid(x):continue
            k=identity(x)
            if k not in frozen:
                frozen[k]={**x,"status":"PENDING","actual":None,
                            "absolute_error":None,"direction_correct":None,
                            "grade_source":None}
                added+=1
    final_index={}
    for x in finals.get("records",[]):
        if x.get("status")!="GRADED" or x.get("stat")!="PTS" or x.get("final_source") not in FINAL_SOURCES:
            continue
        k=identity(x)
        if k not in final_index:final_index[k]=x
        elif final_index[k]!=x:final_index[k]=None
    graded=0
    for k,p in frozen.items():
        if p.get("status")=="GRADED":continue
        match=final_index.get(k)
        if not match or not match.get("source_game_id"):continue
        try:
            actual=float(match["actual"])
            predicted=float(p["projection"]);line=float(p["line"])
        except (TypeError,KeyError,ValueError):continue
        if not math.isfinite(actual) or not 0<=actual<=100:continue
        p["status"]="GRADED";p["actual"]=actual
        p["absolute_error"]=round(abs(predicted-actual),4)
        p["direction_correct"]=(predicted>line)==(actual>line) if predicted!=line and actual!=line else None
        p["grade_source"]=match["final_source"]
        p["source_game_id"]=match["source_game_id"]
        graded+=1
    rows=sorted(frozen.values(),key=lambda x:(x["start"],x["player_id"],x["game"]))
    eligible=[x for x in rows if x.get("status")=="GRADED" and isinstance(x.get("direction_correct"),bool)]
    scored=[x for x in rows if x.get("status")=="GRADED"]
    return {"status":"IMMUTABLE_PREGAME_NEW_MODEL_POINTS",
        "model":"TRAINED_2022_24_LAGGED_MATCHUP_POINTS_CHALLENGER",
        "records":rows,"recorded":len(rows),"new_locked":added,
        "new_grades":graded,"graded":len(scored),
        "pending":len(rows)-len(scored),
        "observed_mae":round(sum(x["absolute_error"] for x in scored)/len(scored),4) if scored else None,
        "direction_eligible":len(eligible),
        "direction_hit_rate":round(sum(x["direction_correct"] for x in eligible)/len(eligible),4) if eligible else None,
        "betting_edge_validated":False,"profit_not_calculated":True,
        "legacy_grade_modified":False,"no_retroactive_prediction_recalculation":True}

def main():
    prior=json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    source=json.loads(LIVE.read_text()) if LIVE.exists() else {}
    finals=json.loads(FINAL.read_text()) if FINAL.exists() else {}
    report=update(prior,source,finals)
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    LEDGER.write_text(json.dumps(report,indent=2)+"\n")
    print("NEW_MODEL_PREGAME_LEDGER",json.dumps({
        k:report[k] for k in ("recorded","new_locked","new_grades","graded","pending","observed_mae","direction_hit_rate")}),flush=True)

if __name__=="__main__":
    main()

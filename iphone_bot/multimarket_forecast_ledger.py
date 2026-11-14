"""Freeze new four-market projections before tipoff; grade verified final boxes.

No recalculation after game start, no guessed results and no changes to
existing Combined AI grading. Each independently observed pretip standard
threshold is its own immutable version; original grades are never repriced.
"""
import json,math
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/lagged_matchup_live_all_markets.json"
LEDGER=ROOT/"docs/lagged_matchup_all_market_ledger.json"
FINAL=ROOT/"docs/ai_forecast_actual_ledger.json"
VOID=ROOT/"docs/espn_injury_void_ledger.json"

def with_voids(finals,void_path=None):
    path=Path(void_path) if void_path else VOID
    if not path.exists():return finals
    additional=json.loads(path.read_text()).get("records",[])
    return {**(finals or {}),"records":list((finals or {}).get("records",[]))+additional}
STATS={"PTS","REB","AST","PRA"}

def utc(value):
    try:
        t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if t.tzinfo is None or t.utcoffset() is None:raise ValueError
        return t.astimezone(timezone.utc)
    except (TypeError,ValueError) as exc:raise ValueError("Naive/invalid timestamp") from exc

def outcome_key(x):
    """Final player totals belong to player/game/stat, not one quote price."""
    return tuple(str(x.get(z) or "") for z in ("player_id","team","game","start","stat"))

def key(x):
    """Each genuinely frozen standard line has independent gradeability."""
    return (*outcome_key(x), str(float(x["line"])))

def valid(x):
    if not isinstance(x,dict) or x.get("stat") not in STATS or not all(x.get(k) for k in ("player_id","team","game")):
        return False
    if (x.get("pickem_tier")!="standard" or
        x.get("standard_line_two_sided_verified") is not True or
        x.get("research_only") is not True or
        x.get("calibrated_probability") is not None):return False
    try:
        captured=utc(x["captured_at"]);tip=utc(x["start"]);quote=utc(x["market_updated"])
        value=float(x["projection"]);line=float(x["line"])
        return (quote<=captured<tip and
            all(math.isfinite(z) for z in (value,line)) and
            0<=value<=200 and 0<=line<=200)
    except (KeyError,ValueError,TypeError):return False

def merge(previous,feed,finals):
    frozen={}
    for x in previous.get("records",[]) if previous.get("status")=="FROZEN_NEW_AI_ALL_MARKET" else []:
        if valid(x):
            k=key(x)
            if k in frozen and frozen[k]!=x:raise ValueError("Contradictory frozen market")
            frozen[k]=dict(x)
    new=0
    if feed.get("status")=="LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED":
        for x in sorted(feed.get("predictions",[]),key=lambda q:str(q.get("captured_at",""))):
            if not valid(x):continue
            k=key(x)
            if k not in frozen:
                frozen[k]={**x,"grade":"PENDING","actual":None,
                           "absolute_error":None,"direction_hit":None,
                           "final_source":None}
                new+=1
    outcomes={}
    # Exact final identity is shared across line versions. A verified DNP
    # excludes ALL of that player's frozen thresholds, without recording
    # a win/loss, a synthetic zero, or a fake model error.
    allowed_finals={"NBA_CDN_FINAL","ESPN_FINAL"}
    # The upstream final grader also emits explicit DNP from official final boxes.
    # Status, reason, null actual and exact event identity remain mandatory.
    allowed_dnp=allowed_finals | {"NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
                 "VERIFIED_FINAL_BOXSCORE_DNP_CROSSCHECKED",
                 "ESPN_FINAL_BOX_ABSENT_INJURY_LISTED"}
    for x in finals.get("records",[]):
        if not isinstance(x,dict) or x.get("stat") not in STATS or not x.get("source_game_id"):
            continue
        status=x.get("status")
        if status=="GRADED" and x.get("final_source") in allowed_finals:
            pass
        elif (status=="EXCLUDED_VERIFIED_DNP" and
              x.get("final_source") in allowed_dnp and
              x.get("actual") is None and x.get("verified_dnp_reason")):
            pass
        else:
            continue
        k=outcome_key(x)
        # Contradictory official finals must fail closed rather than silently
        # choose an arbitrary result from the published ledger.
        if k in outcomes and outcomes[k]!=x:outcomes[k]=None
        elif k not in outcomes:outcomes[k]=x
    new_grades=0
    new_verified_exclusions=0
    for k,x in frozen.items():
        if x.get("grade")!="PENDING":continue
        outcome=outcomes.get(outcome_key(x))
        if not outcome:continue
        if outcome["status"]=="EXCLUDED_VERIFIED_DNP":
            x["grade"]="EXCLUDED_VERIFIED_DNP"
            x["actual"]=None
            x["absolute_error"]=None
            x["direction_hit"]=None
            x["final_source"]=outcome["final_source"]
            x["source_game_id"]=outcome["source_game_id"]
            x["verified_dnp_reason"]=outcome["verified_dnp_reason"]
            new_verified_exclusions+=1
            continue
        try:
            a=float(outcome["actual"]);p=float(x["projection"]);q=float(x["line"])
        except (ValueError,TypeError,KeyError):continue
        if not math.isfinite(a) or not 0<=a<=200:continue
        side=x.get("estimated_hit_chance",{}).get("modeled_direction")
        hit=(a>q) if side=="More" else (a<q) if side=="Less" else None
        if a==q:hit=None
        x["grade"]="GRADED";x["actual"]=a
        x["absolute_error"]=round(abs(a-p),4)
        x["direction_hit"]=hit
        x["final_source"]=outcome["final_source"]
        x["source_game_id"]=outcome["source_game_id"]
        new_grades+=1
    values=sorted(frozen.values(),key=lambda x:(x["start"],x["player_id"],x["stat"],float(x["line"])))
    by_stat={}
    for stat in sorted(STATS):
        arr=[x for x in values if x["stat"]==stat]
        graded=[x for x in arr if x.get("grade")=="GRADED"]
        excluded=[x for x in arr if x.get("grade")=="EXCLUDED_VERIFIED_DNP"]
        eligible=[x for x in graded if isinstance(x.get("direction_hit"),bool)]
        by_stat[stat]={"recorded":len(arr),"graded":len(graded),
          "verified_dnp_excluded":len(excluded),
          "pending":len(arr)-len(graded)-len(excluded),
          "mae":round(sum(x["absolute_error"] for x in graded)/len(graded),4) if graded else None,
          "modeled_side_hit_rate":round(sum(x["direction_hit"] for x in eligible)/len(eligible),4) if eligible else None,
          "direction_eligible":len(eligible)}
    return {"status":"FROZEN_NEW_AI_ALL_MARKET","records":values,
            "new_pregame_frozen":new,"new_verified_grades":new_grades,
            "new_verified_dnp_exclusions":new_verified_exclusions,
            "market_metrics":by_stat,
            "existing_grades_modified":False,
            "probabilities_calibrated":False,
            "no_retroactive_prediction_recalculation":True}

def main():
    older=json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    fresh=json.loads(SOURCE.read_text()) if SOURCE.exists() else {}
    final=with_voids(json.loads(FINAL.read_text()) if FINAL.exists() else {})
    out=merge(older,fresh,final)
    LEDGER.write_text(json.dumps(out,indent=2)+"\n")
    print("FROZEN_NEW_AI_ALL_MARKET",json.dumps({
      "new":out["new_pregame_frozen"],"graded":out["new_verified_grades"],
      "dnp_excluded":out["new_verified_dnp_exclusions"],
      "by_stat":out["market_metrics"]}),flush=True)

if __name__=="__main__":main()

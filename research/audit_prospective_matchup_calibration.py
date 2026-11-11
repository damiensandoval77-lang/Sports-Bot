"""Prospective calibration audit using only pretip archived model probabilities.

Final outcomes MUST come from immutable standard-line graded ledger; joined by
actual player/team/opponent/game/stat/line/side and original quote time as
proved by source capture. Never count DNP, old-only predictions, demon/goblin
lines, non-final scores or historical-over percentages. This EVALUATES the
existing forecasts, and does not train probabilities on future results.
"""
import argparse,json,math
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from research.archive_matchup_forecasts import STATUS as ARCHIVE_STATUS
from research.publish_matchup_shadow_guard import validate

READY_TOTAL=200
READY_MARKET=40
MIN_DISTINCT_DAYS=7
MAX_ECE=.075
MAX_BRIER=.25
MODEL="POSITION_V_POSITION_DEF_RATING_RESEARCH_ANALYTIC_V1"
def stamp(value):
    if not isinstance(value,str):raise ValueError("timestamp missing")
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("missing timezone")
    return dt.astimezone(timezone.utc)
def key(row):
    return (str(row.get("player_id") or ""),str(row.get("team") or ""),
      str(row.get("opponent") or ""),str(row.get("start") or ""),
      str(row.get("stat") or ""),float(row.get("line") or 0))
def day(s):
    from zoneinfo import ZoneInfo
    return stamp(s).astimezone(ZoneInfo("America/New_York")).date().isoformat()
def report(archive,ledger,*,checked_at):
    now=stamp(checked_at)
    if archive.get("status")!=ARCHIVE_STATUS or not isinstance(archive.get("forecasts"),list):
        raise ValueError("missing prospective forecast archive")
    if ledger.get("status")!="FROZEN_NEW_AI_ALL_MARKET":
        raise ValueError("unexpected final source ledger")
    original=defaultdict(list)
    for g in ledger.get("records",[]):
        if (g.get("pickem_tier")!="standard" or
            g.get("standard_line_two_sided_verified") is not True or
            not g.get("player_id") or not g.get("team") or
            not g.get("opponent")):continue
        original[key(g)].append(g)
    paired=[]
    exclusions=Counter()
    seen=set()
    scored_outcomes=set()
    # Archive intentionally retains every immutable pregame refresh; a single
    # actual player stat/standard line can only resolve once. Select the
    # earliest *eligible* independently frozen model forecast for that
    # outcome, not the one nearest tipoff or whichever wins after the fact.
    chronological=sorted(archive["forecasts"],
        key=lambda x:str(x.get("captured_at") or ""))
    for x in chronological:
        model=x.get("estimated_hit_chance") or {}
        if model.get("method")!=MODEL or model.get("calibrated") is not False or model.get("research_only") is not True:
            exclusions["unsupported_model"]+=1;continue
        ident=tuple(str(x.get(k) or "") for k in
          ("player_id","team","opponent","stat","start","line","original_side","captured_at"))
        if ident in seen:raise ValueError("duplicate frozen model observation")
        seen.add(ident)
        prob=model.get("modeled_selected_probability")
        if type(prob) not in (float,int) or not math.isfinite(prob) or not 0<=prob<=1:
            exclusions["invalid_probability"]+=1;continue
        try:
            modeled=stamp(x["captured_at"])
            tip=stamp(x["start"])
            if modeled>=tip or modeled>now:
                exclusions["not_known_pretip"]+=1;continue
            provenance=model["source_provenance"]
            if not all(stamp(provenance[k])<=modeled for k in
                       ("position_observed_at","rating_observed_at","player_observed_at","minutes_snapshot_at")):
                exclusions["future_model_factor"]+=1;continue
        except (TypeError,KeyError,ValueError):
            exclusions["unverified_capture"]+=1;continue
        matches=[g for g in original.get(key(x),[]) if
          g.get("estimated_hit_chance",{}).get("modeled_direction","").upper()==x.get("original_side") and
          stamp(g["captured_at"])<=modeled and stamp(g["captured_at"])<tip]
        if len(matches)!=1:
            exclusions["original_line_or_side_not_unique"]+=1;continue
        g=matches[0]
        # Matchup shadow is its OWN prospective capture: the original quote
        # can predate new position/rating observations. Never overwrite the
        # earlier forecast or pretend the new inputs were known at that time.
        if not stamp(g["captured_at"])<=modeled:
            exclusions["model_precedes_verified_original_quote"]+=1;continue
        if tip>now:
            exclusions["future_game_not_played"]+=1;continue
        if g.get("grade")=="EXCLUDED_VERIFIED_DNP":
            exclusions["verified_dnp_void"]+=1;continue
        if (g.get("grade")!="GRADED" or g.get("final_source") not in ("NBA_CDN_FINAL","ESPN_FINAL") or
            type(g.get("direction_hit")) is not bool or
            type(g.get("actual")) not in (int,float) or not math.isfinite(g["actual"])):
            exclusions["awaiting_independently_verified_final_grade"]+=1;continue
        if g["actual"]==g["line"]:
            exclusions["push_excluded"]+=1;continue
        y=int(g["direction_hit"])
        # Strict standard line grading must agree with original side.
        correct=(g["actual"]>g["line"]) if x["original_side"]=="MORE" else (g["actual"]<g["line"])
        if int(correct)!=y:raise ValueError("grade disagrees with actual vs original line")
        orig=g.get("estimated_hit_chance") or {}
        baseline=orig.get("modeled_selected_probability")
        if type(baseline) not in (int,float) or not math.isfinite(baseline) or not 0<=baseline<=1:
            exclusions["baseline_probability_invalid"]+=1;continue
        # A player-game/market/line/side has ONE resolved betting outcome.
        # Keep later snapshots in the archive for research transparency, but
        # never count them as independent hit-rate/calibration observations.
        outcome_identity=(str(x["player_id"]),str(x["team"]),str(x["opponent"]),
                          str(x["start"]),str(x["stat"]),float(x["line"]),
                          str(x["original_side"]))
        if outcome_identity in scored_outcomes:
            exclusions["repeated_model_snapshot_same_outcome"]+=1
            continue
        scored_outcomes.add(outcome_identity)
        paired.append({"market":x["stat"],"date":day(x["start"]),"prob":float(prob),
                       "baseline":float(baseline),"hit":y,"player_id":x["player_id"],
                       "start":x["start"],"source_game_id":g.get("source_game_id")})
    def metrics(rows):
        n=len(rows)
        if not n:return {"n":0,"brier":None,"baseline_brier":None,"log_loss":None,
                        "ece_5_bin":None,"observed_hit_rate":None}
        brier=sum((r["prob"]-r["hit"])**2 for r in rows)/n
        prior=sum((r["baseline"]-r["hit"])**2 for r in rows)/n
        logloss=sum(-r["hit"]*math.log(max(1e-6,r["prob"]))-
                   (1-r["hit"])*math.log(max(1e-6,1-r["prob"])) for r in rows)/n
        parts=defaultdict(list)
        for r in rows:parts[min(4,int(r["prob"]*5))].append(r)
        ece=sum(len(z)/n*abs(sum(r["prob"] for r in z)/len(z)-
                sum(r["hit"] for r in z)/len(z)) for z in parts.values())
        return {"n":n,"brier":round(brier,5),"baseline_brier":round(prior,5),
                "log_loss":round(logloss,5),"ece_5_bin":round(ece,5),
                "observed_hit_rate":round(sum(r["hit"] for r in rows)/n,5),
                "bins":[{"range":str(i*20)+"-"+str((i+1)*20)+"%",
                  "n":len(parts[i]),"mean_prediction":round(sum(r["prob"] for r in parts[i])/len(parts[i]),4) if parts[i] else None,
                  "observed_hit_rate":round(sum(r["hit"] for r in parts[i])/len(parts[i]),4) if parts[i] else None}
                  for i in range(5)]}
    market={s:metrics([x for x in paired if x["market"]==s]) for s in ("PTS","REB","AST","PRA")}
    total=metrics(paired)
    dates=sorted({r["date"] for r in paired})
    reason=[]
    if total["n"]<READY_TOTAL:reason.append("INSUFFICIENT_PROSPECTIVE_GRADED_SAMPLES")
    if len(dates)<MIN_DISTINCT_DAYS:reason.append("INSUFFICIENT_INDEPENDENT_GAME_DATES")
    if any(m["n"]<READY_MARKET for m in market.values()):
        reason.append("INSUFFICIENT_PER_MARKET_SAMPLES")
    if total["n"] and total["brier"]>=total["baseline_brier"]:
        reason.append("NO_PAIRED_BRIER_IMPROVEMENT_OVER_FROZEN_BASELINE")
    if total["n"] and (total["ece_5_bin"]>MAX_ECE or total["brier"]>MAX_BRIER):
        reason.append("CALIBRATION_THRESHOLDS_NOT_MET")
    return {"status":"PROSPECTIVE_MATCHUP_CALIBRATION_AUDIT",
       "checked_at":checked_at,"forecast_archive_count":len(archive["forecasts"]),
       "paired_final_grades":len(paired),
       "unique_outcome_policy":"ONE_EARLIEST_ELIGIBLE_PREGAME_SNAPSHOT_PER_PLAYER_GAME_MARKET_LINE_SIDE",
       "completed_distinct_dates":len(dates),
       "first_graded_date":dates[0] if dates else None,
       "last_graded_date":dates[-1] if dates else None,
       "total":total,"per_market":market,"exclusions":dict(sorted(exclusions.items())),
       "eligibility_gate_passed":not reason,
       "calibration_certified":False,
       "promotion_blockers":reason,
       "line_policy":"ORIGINAL_VERIFIED_STANDARD_ONLY_NO_DEMON_OR_GOBLIN",
       "note":"Strict prospective accuracy measurement. Passing descriptive thresholds alone does not train or certify a calibrated replacement; separate date-ordered calibration required."}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",default="docs/matchup_shadow_archive.json")
    p.add_argument("--ledger",default="docs/lagged_matchup_all_market_ledger.json")
    p.add_argument("--output",default="docs/matchup_calibration_report.json")
    a=p.parse_args()
    r=report(json.loads(Path(a.archive).read_text()),
      json.loads(Path(a.ledger).read_text()),
      checked_at=datetime.now(timezone.utc).isoformat())
    Path(a.output).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:r[k] for k in
      ("status","forecast_archive_count","paired_final_grades","completed_distinct_dates","total","promotion_blockers")},indent=2))
if __name__=="__main__":main()

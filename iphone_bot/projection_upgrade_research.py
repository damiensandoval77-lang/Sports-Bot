"""Research-only opportunity, injury, defender V4 and 10k-simulation validation.

All snapshots are captured before tipoff and immutable. A same-game injury
status must be sourced from a report published before the prediction and
matching the event date. No fresh 2026-27 defender matchups are implied by a
2025-26 research archive. This file NEVER modifies a live projection or a
displayed probability.
"""
import hashlib
import json
import math
import random
from collections import Counter,defaultdict
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path

try:
    from .paper_pick_pipeline import utc
except ImportError:
    from paper_pick_pipeline import utc

ROOT=Path(__file__).resolve().parents[1]
BOARD=ROOT/"docs/ai_comparisons.json"
INJURY=ROOT/"docs/injury_context.json"
PAPER=ROOT/"docs/paper_pick_ledger.json"
LEDGER=ROOT/"docs/projection_upgrade_ledger.json"
STATUS=ROOT/"docs/projection_upgrade_status.json"
MARKETS=("PTS","REB","AST","PRA")
MIN_RESIDUALS=1000
SIMULATIONS=10000
SOURCE="RESEARCH_ONLY_PREGAME_LOCKED_CONDITIONAL_PROJECTIONS"


def valid(value):
    if value is None or isinstance(value,bool):return None
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):return None


def identity(row):
    return "|".join((utc(row["event_start"]).isoformat(),
            str(row["player_id"]),str(row["market"]),
            format(float(row["line"]),".10g")))


def official_injuries(feed,game_start,capture):
    """Only event-day, earlier-issued, verified official NBA statuses."""
    if feed.get("status")!="OFFICIAL_NBA_REPORT_VERIFIED" or feed.get("injury_data_verified") is not True:
        return [],"UNVERIFIED_REPORT"
    try:
        issued=utc(feed["report_issued_at"])
        generated=utc(feed["generated_at"])
        if issued>capture or generated>capture:return [],"FUTURE_INJURY_REPORT"
        if (capture-issued).total_seconds()>24*3600:return [],"STALE_INJURY_REPORT"
    except (ValueError,KeyError,TypeError):
        return [],"UNVERIFIED_REPORT_DATE"
    # NBA injury rows must explicitly carry the calendar date of the game.
    game_day=game_start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    rows=[p for p in feed.get("players",[]) if p.get("game_date")==game_day
          and str(p.get("status","")).lower() in
          ("out","doubtful","questionable","probable","available")]
    return rows,"OFFICIAL_SAME_DAY_VERIFIED" if rows else "NO_SAME_DAY_PLAYER_STATUS"


def snapshot(board,injury,existing,at):
    captured=utc(at)
    if board.get("status")!="EXPERIMENTAL_NON_CALIBRATED" or board.get("verified_current_matchups") is not True:
        raise ValueError("Board not verified")
    age=(captured-utc(board["generated_at"])).total_seconds()
    if age<0 or age>45*60:raise ValueError("Board must be captured within 45 minutes of generation")
    old=list(existing)
    seen={identity(r) for r in old}
    counters=Counter()
    for item in board.get("comparisons",[]):
        try:
            if item.get("stat") not in MARKETS:continue
            start=utc(item["start"])
            if start<=captured:continue
            pid=str(item["player_id"])
            original=valid(item.get("projection"))
            combined=valid(item.get("combined_projection"))
            line=valid(item.get("line"))
            if original is None or combined is None or line is None:continue
            row={"event_start":start.isoformat(),"captured_at":captured.isoformat(),
                 "player_id":pid,"player":str(item.get("player","")),
                 "team":str(item.get("team","")),
                 "game":str(item.get("game","")),
                 "market":item["stat"],"line":line,
                 "original_projection":original,
                 "combined_projection":combined,
                 "source":SOURCE,
                 "v4_shadow_projection":None,
                 "v4_shadow_status":"AWAITING_VERIFIED_2026_27_DEFENDER_ROTATIONS",
                 "applied_to_live_ai":False,"simulated_probability_modified":False}
            k=identity(row)
            if k in seen:continue
            # Historical research data only, not evidence of current assignments.
            minutes=item.get("minutes_research") or {}
            injury_minutes=item.get("injury_minutes_research") or {}
            shots=item.get("shot_profile_research") or {}
            estimated=valid(minutes.get("expected_minutes"))
            volume=valid(shots.get("expected_fga"))
            original_min=valid(minutes.get("observed_l5"))
            row["opportunity"]={"projected_minutes_unverified":estimated,
                "observed_last5_minutes":original_min,
                "expected_fga_unverified":volume,
                "minutes_delta_unverified":(
                    round(estimated-original_min,2)
                    if estimated is not None and original_min is not None else None),
                "source":"PREGAME_RECENT_PLAYER_GAMES_NOT_LINEUP_CONFIRMED"}
            all_statuses,status=official_injuries(injury,start,captured)
            row["injury_report_status"]=status
            # Only teammates explicitly marked OUT with the correct verified
            # report game date may be used to label a conditional scenario.
            out_team=[p for p in all_statuses if
                str(p.get("team",""))==row["team"] and
                str(p.get("player_id",""))!=pid and
                str(p.get("status","")).lower()=="out"]
            row["verified_out_teammate_ids"]=sorted({str(p["player_id"]) for p in out_team})
            # These are *observed* historical teammate on/off production
            # splits already computed pregame; retain provenance and coverage,
            # not a fabricated causal boost or a same-day learned outcome.
            observed=[]
            for split in item.get("teammate_absence_splits",[]):
                if not isinstance(split,dict):continue
                with_count=split.get("with_games")
                without_count=split.get("without_games")
                if not isinstance(with_count,int) or not isinstance(without_count,int):continue
                if min(with_count,without_count)<3:continue
                observed.append({"status":"OBSERVED_NON_CAUSAL_SPLIT",
                    "teammate":split.get("teammate"),
                    "with_games":with_count,"without_games":without_count,
                    "with_avg":valid(split.get("with_avg")),
                    "without_avg":valid(split.get("without_avg"))})
            row["teammate_on_off_observed"]=observed
            if observed:counters["observed_teammate_on_off"]+=1
            scenario=valid(injury_minutes.get("scenario_minutes"))
            scenario_id=str(injury_minutes.get("teammate_id") or "")
            scenario_ok=(status=="OFFICIAL_SAME_DAY_VERIFIED" and
                injury_minutes.get("status")=="HISTORICAL_SCENARIO_RESEARCH_ONLY" and
                scenario_id in row["verified_out_teammate_ids"] and
                estimated is not None and estimated>0 and scenario is not None)
            row["injury_scenario"]={
                "status":"PREGAME_CONDITIONAL_NOT_CAUSAL" if scenario_ok
                         else "NO_VERIFIED_PREGAME_MINUTES_SCENARIO",
                "candidate_teammate_id":scenario_id if scenario_ok else None,
                "scenario_minutes":scenario if scenario_ok else None,
                "baseline_minutes":estimated,
                "scenario_points_projection":None,
                "research_only":True}
            # Never copy minutes directly into scoring model without a
            # validated usage/efficiency relationship for this market.
            if scenario_ok:counters["conditional_minutes_scenarios"]+=1
            if status=="OFFICIAL_SAME_DAY_VERIFIED":counters["official_report_matched"]+=1
            if volume is not None:counters["shot_opportunity_available"]+=1
            if estimated is not None:counters["minutes_available"]+=1
            row["status"]="PREGAME_LOCKED"
            old.append(row)
            seen.add(k)
            counters["new"]+=1
        except (ValueError,KeyError,TypeError):
            counters["invalid_comparisons"]+=1
    return old,dict(counters)


def finished_unique(paper_rows):
    """Earliest locked independent book per player/event/market/side."""
    groups={}
    for r in paper_rows:
        if r.get("status")!="SETTLED" or r.get("market") not in MARKETS:continue
        try:
            start=utc(r["event_start"]);at=utc(r["captured_at"])
            if at>=start:continue
            p=valid(r.get("original_projection"))
            actual=valid(r.get("actual"))
            line=valid(r.get("line"))
            if p is None or actual is None or line is None:continue
            key=(str(r["player_id"]),start.isoformat(),r["market"])
            old=groups.get(key)
            if old is None or at<utc(old["captured_at"]):
                groups[key]=r
        except (ValueError,TypeError,KeyError):continue
    return list(groups.values())


def research_simulations(paper_rows):
    """10,000 seeded residual-bootstrap runs only if past out-of-time samples exist.

    For each chronological date, past settled outcomes are the ONLY eligible
    calibration distribution. Evaluation is prospective relative to the game,
    and no 100% probabilities can be asserted from finite bootstrap runs.
    """
    settled=finished_unique(paper_rows)
    by_market=defaultdict(list)
    for r in settled:by_market[r["market"]].append(r)
    report={}
    for stat in MARKETS:
        rows=sorted(by_market[stat],key=lambda r:(utc(r["event_start"]),str(r["player_id"])))
        days=sorted({utc(r["event_start"]).date().isoformat() for r in rows})
        results=[]
        past=[]
        for day in days:
            current=[r for r in rows if utc(r["event_start"]).date().isoformat()==day]
            if len(past)>=MIN_RESIDUALS:
                residuals=[float(r["actual"])-float(r["original_projection"]) for r in past]
                seed=int(hashlib.sha256((stat+day).encode()).hexdigest()[:15],16)
                rng=random.Random(seed)
                errors=rng.choices(residuals,k=SIMULATIONS)
                # Same 10k draw for all rows from this event date. Predictions
                # are evaluated against independently completed outcomes.
                for r in current:
                    original=float(r["original_projection"]);line=float(r["line"])
                    if original==line or float(r["actual"])==line:continue
                    want_over=original>line
                    prob=(sum((original+x>line) if want_over else (original+x<line) for x in errors)+.5)/(SIMULATIONS+1)
                    hit=int((float(r["actual"])>line)==want_over)
                    results.append((prob,hit))
            # SAME-DATE outcomes become available only after scoring the day.
            past.extend(current)
        n=len(results)
        report[stat]={"status":"PREGAME_CHRONOLOGICAL_10K_SIM_AUDIT" if n>=30 else
            "AWAITING_AT_LEAST_1000_PRIOR_SETTLED_GAMES_AND_30_LATER_TESTS",
            "completed_independent_markets":len(rows),
            "evaluated_later_markets":n,
            "simulation_count":SIMULATIONS,
            "brier_score":round(sum((p-y)**2 for p,y in results)/n,4) if n else None,
            "average_prediction":round(sum(p for p,_ in results)/n,4) if n else None,
            "observed_hit_rate":round(sum(y for _,y in results)/n,4) if n else None,
            "changes_live_probabilities":False}
    return report


def grade_shadow(ledger,paper_rows):
    """Paired MAE only for actually captured V4 shadows; never backfill."""
    graded={}
    for row in finished_unique(paper_rows):
        key=(utc(row["event_start"]).isoformat(),str(row["player_id"]),row["market"])
        graded[key]=float(row["actual"])
    scores=[]
    for row in ledger:
        shadow=valid(row.get("v4_shadow_projection"))
        if shadow is None:continue
        try:
            if utc(row["captured_at"])>=utc(row["event_start"]):continue
            key=(utc(row["event_start"]).isoformat(),str(row["player_id"]),row["market"])
            if key in graded:
                actual=graded[key]
                scores.append((abs(actual-row["combined_projection"]),abs(actual-shadow),row["market"]))
        except (ValueError,TypeError,KeyError):continue
    return {"status":"PAIRED_V4_SHADOW_SCORED" if len(scores)>=30 else
            "AWAITING_CURRENT_SEASON_VERIFIED_V4_AND_SETTLED_GAMES",
            "paired_markets":len(scores),
            "combined_mae":round(sum(x[0] for x in scores)/len(scores),4) if scores else None,
            "v4_mae":round(sum(x[1] for x in scores)/len(scores),4) if scores else None,
            "v4_live_applied":False}


def run(board,injury,paper_rows,existing,at):
    ledger,counts=snapshot(board,injury,existing,at)
    settled=finished_unique(paper_rows)
    return ledger,{"generated_at":utc(at).isoformat(),
        "status":"OPPORTUNITY_V4_SHADOW_AND_10K_CALIBRATION_RESEARCH_ONLY",
        "locked_samples":len(ledger),"new_samples":counts.get("new",0),
        "features_covered":counts,
        "settled_independent_paper_markets":len(settled),
        "injury_context":"VERIFIED_SAME_GAME_OFFICIAL_REPORT_ONLY",
        "lineup_confirmations_automated":False,
        "teammate_splits":"OBSERVATIONAL_AND_SAMPLE_GATED",
        "defender_v4":grade_shadow(ledger,paper_rows),
        "simulation_audit":research_simulations(paper_rows),
        "live_combined_ai_unchanged":True,
        "live_simulated_hit_percentages_unchanged":True,
        "promotion_gate":"NO_LIVE_ADJUSTMENT_WITHOUT_PRE_GAME_VALIDATION"}


def main():
    board=json.loads(BOARD.read_text())
    injury=json.loads(INJURY.read_text()) if INJURY.exists() else {}
    paper=json.loads(PAPER.read_text()).get("records",[]) if PAPER.exists() else []
    existing=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    now=datetime.now(timezone.utc).isoformat()
    try:
        ledger,report=run(board,injury,paper,existing,now)
    except ValueError as error:
        # A scheduled research-only refresh can update settlement diagnostics
        # even if there is no fresh pregame AI feed to freeze. It may never
        # fabricate a historical capture from a stale postgame board.
        if "within 45 minutes" not in str(error) and "Board must be" not in str(error):
            raise
        ledger=list(existing)
        report={"generated_at":utc(now).isoformat(),
            "status":"RESEARCH_AUDIT_ONLY_NO_FRESH_PREGAME_BOARD",
            "capture_notice":str(error),
            "locked_samples":len(ledger),"new_samples":0,
            "features_covered":{},
            "settled_independent_paper_markets":len(finished_unique(paper)),
            "injury_context":"VERIFIED_SAME_GAME_OFFICIAL_REPORT_ONLY",
            "lineup_confirmations_automated":False,
            "teammate_splits":"OBSERVATIONAL_AND_SAMPLE_GATED",
            "defender_v4":grade_shadow(ledger,paper),
            "simulation_audit":research_simulations(paper),
            "live_combined_ai_unchanged":True,
            "live_simulated_hit_percentages_unchanged":True,
            "promotion_gate":"NO_LIVE_ADJUSTMENT_WITHOUT_PRE_GAME_VALIDATION"}
    LEDGER.write_text(json.dumps({"version":1,"records":ledger},indent=2)+"\n")
    STATUS.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True),flush=True)


if __name__=="__main__":main()

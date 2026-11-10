"""Immutable pregame injury-minute scenarios and fair postgame evaluation.

Research only. Never modifies the sportsbook paper ledger or live projections.
A comparison is valid only when BOTH forecasts were frozen before tipoff and
a matching official NBA report already named the teammate OUT for that fixture.
"""
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .verified_research_no_play import exclude_pending
except ImportError:
    from verified_research_no_play import exclude_pending
try:
    from .paper_pick_pipeline import expected_opponents
except ImportError:
    from paper_pick_pipeline import expected_opponents

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/injury_minutes_ledger.json"
RESULTS=ROOT/"docs/injury_minutes_results.json"
COMPARISONS=ROOT/"docs/ai_comparisons.json"
INJURIES=ROOT/"docs/injury_context.json"
GAMES=ROOT/"data/nba/current/current_games.json"
BUFFER_SECONDS=5*3600
ET=ZoneInfo("America/New_York")


def utc(value):
    value=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if value.tzinfo is None:raise ValueError("Timezone required")
    return value.astimezone(timezone.utc)


def safe_minutes(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and 0<=n<=60 else None
    except (ValueError,TypeError):
        return None


def identity(row):
    return (str(row["player_id"]),utc(row["event_start"]).isoformat())


def snapshot(comparisons,injury_feed,existing=(),captured_at=None):
    """Freeze one baseline/scenario pair per player/event before game start."""
    captured=utc(captured_at) if captured_at else None
    rows=list(existing)
    seen={identity(r) for r in rows}
    if (injury_feed.get("status")!="OFFICIAL_NBA_REPORT_VERIFIED"
            or injury_feed.get("injury_data_verified") is not True):
        return rows
    try:
        issued=utc(injury_feed["report_issued_at"])
        observed={(str(p["player_id"]),str(p.get("game_date")),str(p.get("team"))):
                  str(p.get("status","")).upper()
                  for p in injury_feed.get("players",[])}
    except (KeyError,TypeError,ValueError):
        return rows
    for market in comparisons.get("comparisons",[]):
        scenario=market.get("injury_minutes_research") or {}
        if scenario.get("status")!="HISTORICAL_SCENARIO_RESEARCH_ONLY":continue
        baseline=safe_minutes(scenario.get("baseline_minutes"))
        alternative=safe_minutes(scenario.get("scenario_minutes"))
        if baseline is None or alternative is None:continue
        if scenario.get("live_adjustment_applied") is not False:continue
        try:
            start=utc(market["start"])
            capture=captured or utc(comparisons["generated_at"])
            teammate=str(scenario["teammate_id"])
            player=str(market["player_id"])
            team=str(market["team"])
            game_date=start.astimezone(ET).date().isoformat()
        except (ValueError,KeyError,TypeError):continue
        if not (issued<=capture<start):continue
        if observed.get((teammate,game_date,team))!="OUT":continue
        if observed.get((player,game_date,team))=="OUT":continue
        if not expected_opponents(market.get("game"),team):continue
        record={"player_id":player,"player":str(market.get("player","")),
                "team":team,"game":str(market["game"]),
                "event_start":start.isoformat(),"captured_at":capture.isoformat(),
                "injury_report_issued_at":issued.isoformat(),
                "injury_source_pdf":injury_feed.get("source_pdf"),
                "verified_out_teammate_id":teammate,
                "verified_out_teammate":str(scenario.get("teammate","")),
                "baseline_minutes":baseline,"scenario_minutes":alternative,
                "status":"PENDING","research_only":True,"live_model_unchanged":True}
        ident=identity(record)
        if ident not in seen:
            rows.append(record)
            seen.add(ident)
    return rows


def settle(rows,completed_games,now=None):
    """Grade only exact player/date/team/opponent matches after a 5h buffer."""
    now=utc(now) if now else datetime.now(timezone.utc)
    indexed=defaultdict(list)
    for game in completed_games:
        indexed[(str(game.get("id")),str(game.get("date")))].append(game)
    output=[]
    for original in rows:
        record=dict(original)
        if record.get("status")!="PENDING":
            output.append(record)
            continue
        try:
            start=utc(record["event_start"])
            if (now-start).total_seconds()<BUFFER_SECONDS:
                output.append(record)
                continue
            if utc(record["captured_at"])>=start:
                record["status"]="INVALID_LATE_CAPTURE"
                output.append(record)
                continue
            date=start.astimezone(ET).date().isoformat()
            opponents=expected_opponents(record["game"],record["team"])
            matches=[g for g in indexed.get((str(record["player_id"]),date),[])
                     if g.get("team")==record["team"] and g.get("opponent") in opponents]
            if len(matches)!=1:
                output.append(record)
                continue
            actual=safe_minutes(matches[0].get("MIN"))
            if actual is None or actual<1:
                output.append(record)
                continue
            record.update(status="SETTLED",actual_minutes=actual,
                          settled_at=now.isoformat(),
                          baseline_abs_error=round(abs(record["baseline_minutes"]-actual),3),
                          scenario_abs_error=round(abs(record["scenario_minutes"]-actual),3))
        except (TypeError,ValueError,KeyError):
            pass
        output.append(record)
    return exclude_pending(output,now=now,minutes_only=True)


def report(rows,now=None):
    """Compare on identical evaluated games; no optional samples are imputed."""
    now=utc(now) if now else datetime.now(timezone.utc)
    done=[r for r in rows if r.get("status")=="SETTLED"]
    pending=[r for r in rows if r.get("status")=="PENDING"]
    verified_dnp=[r for r in rows if r.get("status")=="EXCLUDED_VERIFIED_DNP"]
    before=after=ties=0
    for r in done:
        if r["scenario_abs_error"]<r["baseline_abs_error"]:after+=1
        elif r["scenario_abs_error"]>r["baseline_abs_error"]:before+=1
        else:ties+=1
    n=len(done)
    baseline=sum(r["baseline_abs_error"] for r in done)/n if n else None
    scenario=sum(r["scenario_abs_error"] for r in done)/n if n else None
    return {
        "generated_at":now.isoformat(),"status":"PREGAME_LOCKED_INJURY_MINUTES_RESEARCH",
        "captured":len(rows),"pending":len(pending),"settled":n,
        "verified_dnp_exclusions":len(verified_dnp),
        "accounted_for":n+len(verified_dnp),
        "pending_over_48_hours":sum((now-utc(r["event_start"])).total_seconds()>=48*3600 for r in pending),
        "same_game_comparison":{
            "observations":n,"baseline_mae":round(baseline,3) if n else None,
            "injury_scenario_mae":round(scenario,3) if n else None,
            "scenario_minus_baseline_mae":round(scenario-baseline,3) if n else None,
            "scenario_better_games":after,"baseline_better_games":before,"tied_games":ties,
            "sufficient_sample":n>=30},
        "live_model_unchanged":True,
        "limitations":[
            "Comparisons use exact same player-game outcomes with both forecasts saved before tipoff.",
            "Teammate OUT designations were recorded before tipoff from a date-matched official NBA report.",
            "Historical with/without teammate differences are observational, not causal.",
            "Only explicitly verified final-game DNPs are excluded; other missing minutes remain ungraded.",
            "Small samples and correlated same-team games cannot establish predictive improvement.",
            "Research findings do not alter any live points/rebounds/assists predictions."
        ]
    }


def main():
    rows=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    comparisons=json.loads(COMPARISONS.read_text()) if COMPARISONS.exists() else {}
    injuries=json.loads(INJURIES.read_text()) if INJURIES.exists() else {}
    if comparisons.get("status")=="EXPERIMENTAL_NON_CALIBRATED":
        rows=snapshot(comparisons,injuries,rows)
    games=json.loads(GAMES.read_text()) if GAMES.exists() else []
    rows=settle(rows,games)
    output=report(rows)
    LEDGER.write_text(json.dumps({"version":1,"records":rows},indent=2)+"\n")
    RESULTS.write_text(json.dumps(output,indent=2)+"\n")
    print("INJURY MINUTES VALIDATION:",json.dumps({
        "captured":output["captured"],"pending":output["pending"],
        "settled":output["settled"],**output["same_game_comparison"]
    }),flush=True)


if __name__=="__main__":
    main()

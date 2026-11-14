"""Fail-closed release gate for the ONE NBA + NFL Dame's Picks app.

Read-only inputs; no sportsbook calls, predictions, wagers, or regrading.
A successful page load is not sufficient to certify app readiness.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/"docs"
UTC=dt.timezone.utc
REQUIRED_HOURS=72
MAX_GAP_MINUTES=50

def parse_stamp(value):
    try:
        t=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return t.astimezone(UTC) if t.tzinfo else None
    except (TypeError,ValueError,OverflowError):
        return None

def awaiting_verified_live_result(day, row, scoreboard, now):
    """Only excuse exact pending fixtures observed non-final in a fresh official feed.

    This never creates a grade. Unknown, stale, conflicting, final and overdue
    fixtures remain blocked. There is no assumed final-settlement grace period.
    """
    if not isinstance(row, dict) or not isinstance(scoreboard, dict):
        return False
    stamp = parse_stamp(scoreboard.get("generated_at"))
    if (scoreboard.get("status") != "OBSERVED_NBA_LIVE_SCOREBOARD" or
        scoreboard.get("is_live_score_source") is not True or not stamp or
        not 0 <= (now - stamp).total_seconds() <= 20 * 60):
        return False
    pending = row.get("pending")
    groups = row.get("pending_by_game")
    captured, accounted = row.get("captured"), row.get("accounted_for")
    if (type(pending) is not int or pending <= 0 or
        type(captured) is not int or type(accounted) is not int or
        accounted < 0 or captured != accounted + pending or
        not isinstance(groups, dict) or not groups or
        any(type(v) is not int or v <= 0 for v in groups.values()) or
        sum(groups.values()) != pending):
        return False
    games = scoreboard.get("games")
    if not isinstance(games, list):
        return False
    for name in groups:
        matches = [g for g in games if isinstance(g, dict) and
                   g.get("game") == name and g.get("date_eastern") == day]
        if len(matches) != 1:
            return False
        game = matches[0]
        start = parse_stamp(game.get("start"))
        if (not game.get("id") or game.get("game_state") not in {"pre", "in"} or
            not start or not 0 <= (now - start).total_seconds() <= 6 * 3600 or
            stamp < start or
            start.astimezone(ZoneInfo("America/New_York")).date().isoformat() != day):
            return False
    return True

def evaluate(inputs, now=None, previous=None):
    now=now or dt.datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("Timezone-aware current timestamp required")
    now=now.astimezone(UTC)
    reasons={}
    def check(key, data, max_minutes):
        obj=data if isinstance(data,dict) else {}
        errors=[]
        when=parse_stamp(obj.get("checked_at"))
        age=(now-when).total_seconds()/60 if when else None
        if age is None or age < -5 or age > max_minutes:
            errors.append("MISSING_OR_STALE_REPORT")
        reasons[key]=errors
        return obj,errors

    artifact,errors=check("unified_artifacts",inputs.get("unified_artifacts"),95)
    if artifact.get("status")!="READY" or artifact.get("app",{}).get("state")!="READY":
        errors.append("UNIFIED_APP_ARTIFACTS_NOT_READY")
    if any(artifact.get("sports",{}).get(s,{}).get("state")!="READY" for s in ("NBA","NFL")):
        errors.append("NBA_OR_NFL_ARTIFACTS_NOT_READY")

    browser,errors=check("public_unified_browser",inputs.get("public_unified_browser"),95)
    if browser.get("status")!="READY" or browser.get("browser_render_verified") is not True:
        errors.append("MERGED_BROWSER_NOT_VERIFIED")
    if not str(browser.get("site_url","")).rstrip("/").endswith("/Sports-Bot/dames-picks"):
        errors.append("BROWSER_TARGET_NOT_UNIFIED")
    for sport in ("NBA","NFL"):
        item=browser.get(sport)
        if not isinstance(item,dict) or item.get("selected")!=sport or item.get("loaded") is not True or not isinstance(item.get("rendered"),int) or item["rendered"]<=0:
            errors.append(sport+"_BROWSER_MISSING_CARDS")

    nba,errors=check("nba_production",inputs.get("nba_production"),55)
    if nba.get("status")!="READY" or nba.get("ready_for_trustworthy_picks") is not True:
        errors.append("NBA_PRODUCTION_NOT_READY")
    for name,component in nba.get("components",{}).items():
        if component.get("required") and component.get("state")!="READY":
            errors.append("NBA_FAILED_"+name.upper())

    capture,errors=check("nba_capture",inputs.get("nba_capture"),70)
    # Valid saved picks remain usable, but incomplete standard coverage cannot
    # establish the full-app release certification requested by the owner.
    status=capture.get("status")
    if status not in ("CAPTURE_VERIFIED","CAPTURE_INCOMPLETE"):
        errors.append("PRETIP_CAPTURE_SOURCE_INVALID")
    summary=capture.get("summary") if isinstance(capture.get("summary"),dict) else {}
    missing=summary.get("total_standard_markets_without_frozen_model")
    if type(missing) is not int or missing != 0:
        errors.append("PRIMARY_STANDARD_COVERAGE_INCOMPLETE")
    if status=="CAPTURE_INCOMPLETE":
        issues=capture.get("issues")
        if (not isinstance(issues,list) or not issues or any(
            not isinstance(issue,str) or
            not issue.endswith(": STANDARD_MARKETS_WITHOUT_FROZEN_MODEL")
            for issue in issues)):
            errors.append("REQUIRED_PREGAME_PICK_ARTIFACT_MISSING")
        if not isinstance(summary.get("games_with_line_backed_models"),int) or (
            summary.get("games_with_line_backed_models",0)<summary.get("schedule_games",1)):
            errors.append("SCHEDULED_GAME_WITHOUT_FROZEN_MODEL")
    if status=="CAPTURE_VERIFIED" and summary.get("total_standard_markets_without_frozen_model",0)!=0:
        errors.append("CAPTURE_REPORT_INCONSISTENT")
    grade,errors=check("nba_grading",inputs.get("nba_grading"),90)
    grade_status = grade.get("status")
    if grade_status not in {"ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR", "VERIFIED_FINAL_ROWS_OUTSTANDING"}:
        errors.append("HISTORICAL_AI_FORECASTS_UNRESOLVED")
    days=grade.get("days",{})
    if not isinstance(days,dict) or not days:
        errors.append("GRADING_DATES_MISSING")
    else:
        for day,row in days.items():
            settled = (isinstance(row, dict) and type(row.get("pending")) is int and
                       row["pending"] == 0 and type(row.get("captured")) is int and
                       type(row.get("accounted_for")) is int and row["captured"] >= 0 and
                       row["accounted_for"] == row["captured"])
            live_pending = (grade_status == "VERIFIED_FINAL_ROWS_OUTSTANDING" and
                            awaiting_verified_live_result(day, row, inputs.get("nba_scoreboard"), now))
            if not settled and not live_pending:
                errors.append("GRADING_INCOMPLETE:"+str(day))

    # Strictly validate the picks that reached the public app.
    # Unsupported provider quotes remain separately visible in source
    # diagnostics, but cannot masquerade as frozen, gradeable picks.
    saved,errors=check("published_pick_settlement",
                       inputs.get("published_pick_settlement"),65)
    if saved.get("status")!="READY":
        errors.append("PUBLISHED_PICKS_WITH_INVALID_OR_MISSING_SETTLEMENT")
    counts=saved.get("counts") if isinstance(saved.get("counts"),dict) else {}
    if not isinstance(counts.get("frozen_picks"),int) or counts["frozen_picks"]<1:
        errors.append("NO_FROZEN_PICKS_VERIFIED")

    # NFL historical health artifact currently has no generated_at stamp.
    # Verify its explicit frozen standard-only contract without pretending
    # to know when its data last refreshed.
    nfl=inputs.get("nfl_grading")
    nfl=nfl if isinstance(nfl,dict) else {}
    errors=[]
    reasons["nfl_grading"]=errors
    if nfl.get("official_grading_scope")!="FROZEN_STANDARD_LINE_ONLY":
        errors.append("NFL_STANDARD_GRADE_SCOPE_INVALID")
    if not isinstance(nfl.get("standard_settled"),int) or nfl["standard_settled"]<1:
        errors.append("NFL_STANDARD_SETTLEMENT_NOT_PRESENT")
    pending=nfl.get("standard_pending_picks")
    if type(pending) is not int or pending<0:
        errors.append("NFL_STANDARD_PENDING_COUNT_INVALID")
    elif pending>0:
        errors.append("NFL_PENDING_GRADES_UNRESOLVED")

    failing=[key for key,issues in reasons.items() if issues]
    pass_now=not failing
    previous=previous if isinstance(previous,dict) else {}
    previous_at=parse_stamp(previous.get("checked_at"))
    prev_start=parse_stamp(previous.get("healthy_streak_started_at"))
    continuous=(previous.get("checks_passing") is True and previous_at and prev_start and
                0 <= (now-previous_at).total_seconds()/60 <= MAX_GAP_MINUTES)
    start=prev_start if pass_now and continuous else now if pass_now else None
    healthy_minutes=(now-start).total_seconds()/60 if start else 0
    certified=pass_now and healthy_minutes>=REQUIRED_HOURS*60
    return {
        "checked_at":now.isoformat(),
        "status":"CERTIFIED" if certified else "MONITORING" if pass_now else "DEGRADED",
        "checks_passing":pass_now,
        "release_certified":certified,
        "healthy_streak_started_at":start.isoformat() if start else None,
        "healthy_streak_hours":round(healthy_minutes/60,2),
        "required_consecutive_hours":REQUIRED_HOURS,
        "blocking_checks":failing,
        "checks":{key:{"state":"READY" if not issues else "DEGRADED","issues":issues}
                  for key,issues in reasons.items()},
        "scope":"UNIFIED_DAMES_PICKS_NBA_NFL_RELEASE_GATE",
        "note":"72h sustained clean artifacts and observed public browser, pretip captures, frozen standard-only grading and current source gates; this does not prove predictive accuracy or zero downtime."
    }

def main():
    def load(path):
        try:
            obj=json.loads((DOCS/path).read_text(encoding="utf-8"))
            return obj if isinstance(obj,dict) else {}
        except (OSError,ValueError):
            return {}
    inputs={
        "unified_artifacts":load("dames-picks/unified_readiness.json"),
        "public_unified_browser":load("dames-picks/browser_readiness.json"),
        "nba_production":load("production_readiness.json"),
        "nba_capture":load("tonight_capture_gradeability.json"),
        "nba_grading":load("ai_forecast_coverage_audit.json"),
        "nba_scoreboard":load("nba_scoreboard_independent.json"),
        "nfl_grading":load("nfl/data/grading_health_2026.json"),
        "published_pick_settlement":load("dames-picks/published_pick_settlement.json"),
    }
    report=evaluate(inputs,previous=load("dames-picks/app_release_gate.json"))
    target=DOCS/"dames-picks/app_release_gate.json"
    target.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("DAMES_PICKS_RELEASE_GATE",json.dumps(report))
    return 0 if report["checks_passing"] else 2

if __name__=="__main__":
    raise SystemExit(main())

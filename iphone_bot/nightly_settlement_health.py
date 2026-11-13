"""Date-scoped NBA nightly settlement health, never infer missing results.

Uses saved immutable PrizePicks / paper captures only. Detects settled, pending,
verified void, and overdue unresolved by actual Eastern event start. No network.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import Counter

from iphone_bot.nightly_grade_date_audit import audit, eastern_date
from iphone_bot.reconcile_grading_production import select_dated_report

ROOT=Path(__file__).resolve().parents[1]
ET=ZoneInfo("America/New_York")
OUTPUT=ROOT/"docs/nightly_grade_health.json"

def health(now,paper,pp,form=None,archive=None,summary=None,grace_hours=12,ai_grades=None):
    if now.tzinfo is None:
        raise ValueError("UTC-aware clock required")
    day=(now.astimezone(ET).date()-dt.timedelta(days=1)).isoformat()
    result=audit(day,paper,form,archive,summary,pp)
    pp_rows=[r for r in pp.get("records",[]) if r.get("start") and
             eastern_date(r["start"])==day]
    paper_rows=[r for r in paper.get("records",[]) if r.get("event_start") and
                eastern_date(r["event_start"])==day]
    def overdue(row,field):
        start=dt.datetime.fromisoformat(row[field].replace("Z","+00:00"))
        return row.get("status")=="PENDING" and start.tzinfo is not None and (
            now-start).total_seconds()>=grace_hours*3600
    overdue_pp=[r for r in pp_rows if overdue(r,"start")]
    overdue_paper=[r for r in paper_rows if overdue(r,"event_start")]
    all_started=all(
        (now-dt.datetime.fromisoformat(r["start"].replace("Z","+00:00"))).total_seconds()
        >=grace_hours*3600
        for r in pp_rows
    ) if pp_rows else False
    if overdue_pp or overdue_paper:
        status="OVERDUE_UNRESOLVED_GRADES"
    elif pp_rows and not result["prizepicks_date_pending"] and all_started:
        status="ALL_CAPTURED_PRIZEPICKS_RECORDS_RESOLVED"
    elif pp_rows:
        status="AWAITING_FINALS_OR_SETTLEMENT_GRACE_PERIOD"
    elif paper_rows:
        status="NO_PRIZEPICKS_LOCKED_RECORDS"
    else:
        status="NO_LOCKED_RECORDS_FOR_TARGET_DATE"
    # This is an independent accuracy workflow, not a sportsbook settlement.
    ai = ai_grades or {}
    matching_ai = ai if ai.get("game_date_eastern")==day else {}
    if matching_ai:
        ai_status=matching_ai.get("status","UNKNOWN")
        ai_saved=matching_ai.get("recorded_pregame_forecasts")
        ai_graded=matching_ai.get("graded")
        ai_missing=matching_ai.get("ungraded")
        ai_excluded=matching_ai.get("verified_dnp_exclusions",0)
        ai_accounted=matching_ai.get("accounted_for",None)
    else:
        ai_status="AI_FORECAST_GRADE_REPORT_NOT_PUBLISHED_FOR_DAY"
        ai_saved=ai_graded=ai_missing=ai_excluded=ai_accounted=None
    return {
        "checked_at":now.isoformat(),
        "game_date_eastern":day,
        "status":status,
        "grace_hours_from_scheduled_start":grace_hours,
        "prizepicks_saved":result["prizepicks_date_locked_records"],
        "prizepicks_settled":result["prizepicks_date_settled"],
        "prizepicks_void":result["prizepicks_date_void"],
        "prizepicks_pending":result["prizepicks_date_pending"],
        "prizepicks_overdue":len(overdue_pp),
        "prizepicks_overdue_games":dict(sorted(Counter(r.get("game") for r in overdue_pp).items())),
        "paper_saved":result["locked_paper_records"],
        "paper_pending":result["pending"],
        "paper_overdue":len(overdue_paper),
        "unpriced_forecasts_separate":result["unpriced_pregame_archive_forecasts"],
        "prizepicks_scope_status":status,
        "ai_forecast_accuracy_status":ai_status,
        "ai_forecasts_recorded":ai_saved,
        "ai_forecasts_graded":ai_graded,
        "ai_forecasts_ungraded":ai_missing,
        "ai_forecasts_verified_dnp_excluded":ai_excluded,
        "ai_forecasts_accounted_for":ai_accounted,
        "ai_forecasts_fully_accounted_for":bool(matching_ai and ai_saved and ai_missing==0 and ai_accounted==ai_saved),
        "ai_forecasts_fully_graded":bool(matching_ai and ai_saved and ai_missing==0 and ai_excluded==0 and ai_graded==ai_saved),
        "overall_grading_status":(
            "ALL_CAPTURED_RESEARCH_AND_AI_FORECASTS_ACCOUNTED_FOR"
            if status=="ALL_CAPTURED_PRIZEPICKS_RECORDS_RESOLVED"
            and matching_ai and ai_saved and ai_missing==0 and ai_accounted==ai_saved
            else "PRIZEPICKS_RESOLVED_AI_GRADING_INCOMPLETE"
            if status=="ALL_CAPTURED_PRIZEPICKS_RECORDS_RESOLVED"
            else status),
        "capture_missing":not (pp_rows or paper_rows),
        "complete_slate_not_guaranteed":True,
        "notice":"Only recorded pretip markets assessed; lack of captured picks is not successful grading. Pending is never a loss."
    }

def select_nightly_ai_report(now, load):
    day=(now.astimezone(ET).date()-dt.timedelta(days=1)).isoformat()
    return select_dated_report(day, [load("docs/"+name) for name in (
        "ai_forecast_grade_status.json", "ai_forecast_today_grade_status.json",
        "ai_forecast_grade_status_"+day+".json")])

def main():
    def load(path):
        p=ROOT/path
        return json.loads(p.read_text()) if p.exists() else {}
    now=dt.datetime.now(dt.timezone.utc)
    report=health(now,
                  load("docs/paper_pick_ledger.json"),
                  load("docs/prizepicks_research_ledger.json"),
                  load("docs/current_form.json"),
                  load("docs/ai_no_line_pregame_archive.json"),
                  load("docs/prizepicks_research_results.json"),
                  ai_grades=select_nightly_ai_report(now,load))
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print("NIGHTLY GRADE HEALTH:",json.dumps(report,sort_keys=True))
    if report["status"]=="OVERDUE_UNRESOLVED_GRADES":
        raise SystemExit(2)

if __name__=="__main__":
    main()

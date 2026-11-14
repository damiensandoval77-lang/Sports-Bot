"""Audit archived NBA pretip AI-only forecasts against immutable verified final outcomes.

Observational and fail-closed: never grades games, infers a DNP, or changes
original predictions. Keeps distinct reporting days independent of the
rolling 'today' and 'yesterday' summary files.
"""
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

from iphone_bot.grade_frozen_ai_forecasts import eligible_predictions, key, eastern_day, utc

ROOT=Path(__file__).resolve().parents[1]
ET=ZoneInfo("America/New_York")
RESOLVED={"GRADED","EXCLUDED_VERIFIED_DNP","EXCLUDED_VERIFIED_NONPARTICIPANT"}

def audit(archive,ledger,previous=None,today=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    eligible=eligible_predictions(archive.get("predictions") or [],now)
    saved={}
    for p in eligible:
        ident=key(p)
        if ident in saved:
            raise ValueError("DUPLICATE_ARCHIVE_FORECAST_IDENTITY")
        saved[ident]=p
    resolved={}
    for r in ledger.get("records",[]):
        if r.get("status") not in RESOLVED:
            raise ValueError("UNVERIFIED_OUTCOME_IN_PERMANENT_GRADE_LEDGER")
        ident=key(r)
        if ident in resolved:
            raise ValueError("DUPLICATE_VERIFIED_GRADE_IDENTITY")
        if not r.get("final_source") or not r.get("source_game_id"):
            raise ValueError("VERIFIED_OUTCOME_MISSING_FINAL_SOURCE")
        resolved[ident]=r
    days=defaultdict(lambda:{"captured":0,"graded":0,"void_dnp":0,
                              "excluded_nonparticipant":0,"pending":0,
                              "pending_by_game":Counter()})
    for ident,p in saved.items():
        day=eastern_day(p["start"])
        bucket=days[day]
        bucket["captured"]+=1
        r=resolved.get(ident)
        if r is None:
            bucket["pending"]+=1
            bucket["pending_by_game"][p["game"]]+=1
            continue
        if (r.get("captured_at")!=p.get("captured_at") or
            str(r.get("player_id"))!=str(p.get("player_id")) or
            r.get("team")!=p.get("team") or
            abs(float(r.get("projection",-1))-float(p["projection"]))>1e-5):
            raise ValueError("IMMUTABLE_PRETIP_FORECAST_MISMATCH: "+ident)
        state=r["status"]
        field={"GRADED":"graded","EXCLUDED_VERIFIED_DNP":"void_dnp",
               "EXCLUDED_VERIFIED_NONPARTICIPANT":"excluded_nonparticipant"}[state]
        bucket[field]+=1
    reported=[]
    report_time_adjustments=[]
    for label,report in (("previous",previous),("today",today)):
        if not isinstance(report,dict):
            continue
        date=report.get("game_date_eastern")
        if date not in days:continue
        counted=days[date]
        declared={"captured":report.get("recorded_pregame_forecasts"),
                  "graded":report.get("graded"),
                  "void_dnp":report.get("verified_dnp_exclusions"),
                  "excluded_nonparticipant":report.get("verified_pretip_transfer_exclusions"),
                  "pending":report.get("ungraded")}
        actual={k:counted[k] for k in declared}
        # A persisted day summary is an as-of snapshot. Newly tipped games
        # become eligible after its timestamp without being overdue grades.
        # Adjust only explicitly unresolved new starts; never hide outcomes,
        # changed predictions, arbitrary mismatches or old pending records.
        observed=utc(report.get("generated_at"))
        if declared!=actual and observed and observed<=now:
            new_pending=sum(1 for ident,p in saved.items() if
                eastern_day(p["start"])==date and ident not in resolved and
                observed<=utc(p["start"])<now)
            adjusted={**actual,"captured":actual["captured"]-new_pending,
                      "pending":actual["pending"]-new_pending}
            if new_pending and declared==adjusted:
                actual=adjusted
                report_time_adjustments.append({"report":label,"date":date,
                    "generated_at":observed.isoformat(),
                    "newly_started_unresolved_forecasts":new_pending})
        if declared!=actual:
            raise ValueError("AI_DAY_STATUS_LEDGER_DISAGREEMENT: "+
                             label+" "+date+" "+json.dumps(
                                 {"declared":declared,"verified_ledger":actual},
                                 sort_keys=True))
        reported.append(date)
    normalized={}
    for day,counts in sorted(days.items()):
        n={k:v for k,v in counts.items() if k!="pending_by_game"}
        n["pending_by_game"]=dict(sorted(counts["pending_by_game"].items()))
        n["accounted_for"]=n["graded"]+n["void_dnp"]+n["excluded_nonparticipant"]
        if n["captured"]!=n["accounted_for"]+n["pending"]:
            raise ValueError("AI_FORECAST_COVERAGE_TOTAL_MISMATCH: "+day)
        normalized[day]=n
    return {"status":"ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR" if
                    all(d["pending"]==0 for d in normalized.values()) else
                    "VERIFIED_FINAL_ROWS_OUTSTANDING",
            "checked_at":now.isoformat(),
            "days":normalized,
            "daily_status_reports_crosschecked":reported,
            "daily_report_time_adjustments":report_time_adjustments,
            "verified_historical_outcomes_not_in_rolling_archive":
                len(set(resolved)-set(saved)),
            "note":"Unresolved is not a loss or DNP. Final settlement requires verified player-level results. This audit never changes outcomes."}

def main():
    archive=json.loads((ROOT/"docs/ai_no_line_pregame_archive.json").read_text())
    ledger=json.loads((ROOT/"docs/ai_forecast_actual_ledger.json").read_text())
    def optional(path):
        try:return json.loads((ROOT/path).read_text())
        except (OSError,ValueError):return None
    result=audit(archive,ledger,optional("docs/ai_forecast_grade_status.json"),
                 optional("docs/ai_forecast_today_grade_status.json"))
    out=ROOT/"docs/ai_forecast_coverage_audit.json"
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("NBA AI FORECAST ARCHIVE RECONCILIATION:",json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

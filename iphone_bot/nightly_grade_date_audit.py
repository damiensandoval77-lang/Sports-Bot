"""Audit a specific Eastern-date slate without inventing grades or picks.

Reads immutable paper ledger and observed form summaries. Reports missing
capture separately from missing results; zero pending is NOT a passing grade.
No network access or API credits.
"""
import argparse
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
EASTERN=ZoneInfo("America/New_York")
SETTLED={"SETTLED","VOID_DNP"}
def eastern_date(stamp):
    instant=dt.datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
    if instant.tzinfo is None:raise ValueError("Timestamp missing offset")
    return instant.astimezone(EASTERN).date().isoformat()

def audit(day,ledger,form=None,archive=None,prizepicks_summary=None,prizepicks_ledger=None):
    dt.date.fromisoformat(day)
    records=ledger.get("records") or []
    captured=[r for r in records if r.get("event_start") and eastern_date(r["event_start"])==day]
    counts=Counter(r.get("status","UNLABELED") for r in captured)
    games=sorted({r["game"] for r in captured if r.get("game")})
    pending=[r for r in captured if r.get("status")=="PENDING"]
    settled=sum(counts.get(v,0) for v in SETTLED)
    latest=(form or {}).get("latest_game_date")
    unpriced_forecasts=[p for p in (archive or {}).get("predictions",[])
                        if p.get("start") and eastern_date(p["start"])==day
                        and p.get("line") is None]
    pp_records = [r for r in (prizepicks_ledger or {}).get("records",[])
                  if r.get("start") and eastern_date(r["start"])==day]
    pp_counts=Counter(r.get("status","UNLABELED") for r in pp_records)
    pp_games=sorted({r["game"] for r in pp_records if r.get("game")})
    pp_pending=[r for r in pp_records if r.get("status")=="PENDING"]
    pp_settled=[r for r in pp_records if r.get("status")=="SETTLED"]
    pp_void=[r for r in pp_records if r.get("status") in ("VOID_DNP","VOID")]
    if not captured:
        verdict="NO_LOCKED_PAPER_PICKS_CAPTURED"
    elif pending:
        verdict="PENDING_FINAL_PLAYER_RESULTS"
    elif settled==len(captured):
        verdict="ALL_CAPTURED_PAPER_PICKS_RESOLVED"
    else:
        verdict="CAPTURED_PICKS_WITH_OTHER_UNRESOLVED_STATUS"
    return {
        "game_date_eastern":day,
        "verdict":verdict,
        "locked_paper_records":len(captured),
        "paper_status_counts":dict(sorted(counts.items())),
        "locked_games":games,
        "locked_games_count":len(games),
        "settled_or_verified_void":settled,
        "pending":len(pending),
        "pending_games":sorted({r["game"] for r in pending if r.get("game")}),
        "observed_completed_form_latest_game_date":latest,
        "form_confirmed_through_target_day":bool(latest and latest>=day),
        "unpriced_pregame_archive_forecasts":len(unpriced_forecasts),
        "prizepicks_cumulative_status":(prizepicks_summary or {}).get("status"),
        "prizepicks_cumulative_pending":(prizepicks_summary or {}).get("pending"),
        "prizepicks_date_specific_verified":bool(pp_records) and not pp_pending and
                                               len(pp_settled)+len(pp_void)==len(pp_records),
        "prizepicks_date_locked_records":len(pp_records),
        "prizepicks_date_settled":len(pp_settled),
        "prizepicks_date_void":len(pp_void),
        "prizepicks_date_pending":len(pp_pending),
        "prizepicks_date_status_counts":dict(sorted(pp_counts.items())),
        "prizepicks_date_saved_games":pp_games,
        "prizepicks_date_pending_games":sorted({r["game"] for r in pp_pending if r.get("game")}),
        "prizepicks_pending_record_counts_by_game":dict(sorted(
            Counter(r.get("game","UNKNOWN") for r in pp_pending).items())),
        "prizepicks_pending_distinct_player_stat_markets":len({
            (r.get("game"),r.get("player_id"),r.get("stat"))
            for r in pp_pending}),
        "notes":[
            "Cumulative settled totals do not prove that this date was captured or graded.",
            "No-line forecasts are separate research observations, not locked wager or sportsbook records.",
            "This audit is not proof of a complete NBA slate without independent game-level capture records.",
            "PrizePicks date verification relies on original pretip research ledger and its settlement statuses."
        ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date",help="Eastern YYYY-MM-DD (default yesterday)")
    p.add_argument("--fail-if-ungraded",action="store_true")
    args=p.parse_args()
    day=args.date or (dt.datetime.now(EASTERN).date()-dt.timedelta(days=1)).isoformat()
    def load(file,default):
        pth=ROOT/file
        return json.loads(pth.read_text()) if pth.exists() else default
    report=audit(day,load("docs/paper_pick_ledger.json",{}),
                 load("docs/current_form.json",{}),
                 load("docs/ai_no_line_pregame_archive.json",{}),
                 load("docs/prizepicks_research_results.json",{}),
                 load("docs/prizepicks_research_ledger.json",{}))
    print(json.dumps(report,indent=2))
    if args.fail_if_ungraded and report["verdict"]!="ALL_CAPTURED_PAPER_PICKS_RESOLVED":
        raise SystemExit(1)

if __name__=="__main__":
    main()

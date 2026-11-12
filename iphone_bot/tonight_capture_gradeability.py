"""Independent Eastern-game-date NBA capture and gradeability reconciliation.

Evidence categories deliberately separate:
  source quote observation != frozen AI prediction != line-backed model != graded outcome.
Never create missing picks or infer winners. JSON report is independently auditable.
"""
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
ET=ZoneInfo("America/New_York")
OUT=ROOT/"docs/tonight_capture_gradeability.json"

def eastern_day(value):
    try:
        x=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return x.astimezone(ET).date().isoformat() if x.tzinfo else None
    except (TypeError,ValueError,OverflowError):return None

def reconcile(schedule,quotes,ai,locked,grades,now=None,day=None,research=None,current=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    today=now.astimezone(ET).date().isoformat()
    days=sorted({g.get("date_eastern") for g in schedule.get("games",[])
                 if isinstance(g,dict) and g.get("date_eastern") and g.get("start")
                 and eastern_day(g["start"])==g["date_eastern"]})
    # Keep the active US evening slate in view even after local midnight.
    candidates=[d for d in days if d<=today]
    day=day or (candidates[-1] if candidates else today)
    games=[g for g in schedule.get("games",[]) if isinstance(g,dict)
           and g.get("date_eastern")==day and g.get("game")]
    qs=[q for q in quotes.get("quotes",[]) if
        q.get("source")=="independent_prizepicksapi_com" and
        q.get("is_demo") is False and eastern_day(q.get("starts_at"))==day]
    preds=[p for p in ai.get("predictions",[]) if
           p.get("is_pregame_prediction") is True and p.get("line") is None and
           eastern_day(p.get("start"))==day]
    backed=[p for p in locked.get("records",[]) if
            eastern_day(p.get("start"))==day]
    grade_rows=[p for p in grades.get("records",[]) if
                eastern_day(p.get("start"))==day]
    result={"checked_at":now.isoformat(),"game_date_eastern":day,
            "status":"CAPTURE_INCOMPLETE","games":[],"issues":[],
            "note":"Provider quotes, AI-only forecasts, line-backed frozen predictions and final grades are separate. Missing records never fabricated."}
    if not games:
        result["issues"].append("NO_SCHEDULED_GAMES_FOR_DATE")
    if schedule.get("coverage_complete") is not True:
        result["issues"].append("SCHEDULE_INCOMPLETE")
    if quotes.get("status")!="VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE":
        result["issues"].append("QUOTE_ARCHIVE_INVALID")
    if ai.get("status")!="IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE":
        result["issues"].append("AI_ARCHIVE_INVALID")
    if locked.get("status")!="FROZEN_NEW_AI_ALL_MARKET":
        result["issues"].append("LINE_BACKED_ARCHIVE_INVALID")
    if quotes.get("count")!=len(quotes.get("quotes",[])):
        result["issues"].append("QUOTE_ARCHIVE_COUNT_MISMATCH")
    for game in games:
        name=game["game"]
        q=[x for x in qs if x.get("game")==name]
        a=[x for x in preds if x.get("game")==name]
        l=[x for x in backed if x.get("game")==name]
        standard=[x for x in q if x.get("tier")=="standard"]
        # Compare original standard thresholds, not merely player and stat.
        # A 24.5 freeze must never satisfy capture coverage for a moved 25.5.
        def market_key(x):
            try: threshold=float(x["line"])
            except (TypeError,ValueError,KeyError): threshold=None
            return (x.get("player"),x.get("team"),x.get("stat"),threshold)
        frozen_markets={market_key(x) for x in l}
        standard_markets={market_key(x) for x in standard}
        missing_markets=standard_markets-frozen_markets
        # Keep the exact-quote gap visible, but distinguish a genuine later
        # standard price move from a player/stat with no primary freeze at all.
        # Historical model projections must never be repriced retroactively.
        frozen_identity={key[:3] for key in frozen_markets}
        moved_price_markets={key for key in missing_markets if key[:3] in frozen_identity}
        entirely_unfrozen_markets=missing_markets-moved_price_markets
        # Research receipts are a separate fallback, never validated model picks.
        archived_research=(research or {}).get("records",[]) if (research or {}).get("status")=="IMMUTABLE_PRETIP_STANDARD_QUOTE_AI_RESEARCH" else []
        eligible_research={
            market_key(x) for x in archived_research
            if x.get("game")==name and x.get("research_only") is True
            and x.get("calibrated") is False
            and x.get("grade")=="UNSETTLED_RESEARCH"
            and x.get("more_tier")=="standard" and x.get("less_tier")=="standard"
            and x.get("source")=="independent_prizepicksapi_com"
        }
        research_backed=missing_markets & eligible_research
        no_ai_receipt=missing_markets - eligible_research
        g=[x for x in grade_rows if x.get("game")==name]
        issue=[]
        if not q:issue.append("NO_CAPTURED_PROVIDER_LINES")
        if not a:issue.append("NO_SAVED_PREGAME_AI")
        if standard and not l:issue.append("PROVIDER_QUOTES_WITH_NO_FROZEN_LINE_BACKED_MODEL")
        if missing_markets:issue.append("STANDARD_MARKETS_WITHOUT_FROZEN_MODEL")
        # Only a verified final can create a grade. Do not fail because
        # an actual game is still in progress or yet to start.
        try:started=(now-dt.datetime.fromisoformat(game["start"].replace("Z","+00:00"))).total_seconds()
        except (TypeError,ValueError):started=None
        # Flag *partial* settlement as well as nights with zero grades.
        # The grace window is only a diagnostic, not proof the game went final.
        pending=[x for x in l if x.get("grade")=="PENDING"]
        if started is not None and started>8*3600 and pending:
            issue.append("LINE_BACKED_GRADING_OVERDUE_CHECK_FINAL_FEED")
        row={"game":name,"start":game.get("start"),
             "source_quotes":len(q),
             "standard_source_quotes":len(standard),
             "standard_unique_markets":len(standard_markets),
             "standard_markets_without_frozen_model":len(missing_markets),
             "standard_price_moves_from_original_frozen_line":len(moved_price_markets),
             "standard_player_stat_markets_never_primary_frozen":len(entirely_unfrozen_markets),
             "missing_primary_with_separate_research_receipt":len(research_backed),
             "missing_primary_without_any_ai_receipt":len(no_ai_receipt),
             "unique_provider_player_stat_markets":len({(x.get("player"),x.get("team"),x.get("stat")) for x in q}),
             "frozen_ai_only":len(a),
             "frozen_line_backed":len(l),
             "line_backed_graded":sum(x.get("grade")=="GRADED" for x in l),
             "ai_only_graded":sum(x.get("status")=="GRADED" for x in g),
             "line_backed_pending":len(pending),
             "issues":issue}
        result["games"].append(row)
        result["issues"].extend(name+": "+i for i in issue)
    result["summary"]={"schedule_games":len(games),
       "games_with_saved_source_quotes":sum(g["source_quotes"]>0 for g in result["games"]),
       "games_with_frozen_ai":sum(g["frozen_ai_only"]>0 for g in result["games"]),
       "games_with_line_backed_models":sum(g["frozen_line_backed"]>0 for g in result["games"]),
       "total_quotes":sum(g["source_quotes"] for g in result["games"]),
       "total_standard_source_quotes":sum(g["standard_source_quotes"] for g in result["games"]),
       "total_standard_markets_without_frozen_model":sum(g["standard_markets_without_frozen_model"] for g in result["games"]),
       "total_price_moves_from_original_frozen_line":sum(g["standard_price_moves_from_original_frozen_line"] for g in result["games"]),
       "total_player_stat_markets_never_primary_frozen":sum(g["standard_player_stat_markets_never_primary_frozen"] for g in result["games"]),
       "total_missing_primary_with_separate_research_receipt":sum(g["missing_primary_with_separate_research_receipt"] for g in result["games"]),
       "total_missing_primary_without_any_ai_receipt":sum(g["missing_primary_without_any_ai_receipt"] for g in result["games"]),
       "total_ai_only":sum(g["frozen_ai_only"] for g in result["games"]),
       "total_line_backed":sum(g["frozen_line_backed"] for g in result["games"]),
       "total_line_backed_graded":sum(g["line_backed_graded"] for g in result["games"]),
       "total_ai_only_graded":sum(g["ai_only_graded"] for g in result["games"])}
    from .current_primary_coverage import evaluate as current_coverage
    result["current_upcoming_coverage"]=current_coverage(current or {},locked,games,now)
    result["status"]="CAPTURE_VERIFIED" if not result["issues"] else "CAPTURE_INCOMPLETE"
    return result

def main():
    paths=["docs/nba_schedule.json","docs/prizepicks_pregame_line_archive.json",
           "docs/ai_no_line_pregame_archive.json","docs/lagged_matchup_all_market_ledger.json",
           "docs/ai_forecast_actual_ledger.json",
           "docs/standard_quote_ai_research_archive.json","docs/prizepicks_model_input.json"]
    try:
        records=[json.loads((ROOT/p).read_text()) for p in paths]
        report=reconcile(*records[:5],research=records[5],current=records[6])
    except (OSError,ValueError,TypeError) as exc:
        report={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                "status":"CAPTURE_INCOMPLETE","issues":["INPUT_ERROR:"+type(exc).__name__]}
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("TONIGHT_CAPTURE_GRADEABILITY",json.dumps(report))
    return 0 if report["status"]=="CAPTURE_VERIFIED" else 1
if __name__=="__main__":sys.exit(main())

"""Plan credit-free recovery of stale Sports-Bot production inputs.

Only dispatch existing free-source workflows. Never trigger a paid odds or
PrizePicks collector, fabricate lines, or mark unresolved grades as settled.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
UTC=dt.timezone.utc
ET=ZoneInfo("America/New_York")

def read(root,path):
    try:return json.loads((Path(root)/path).read_text(encoding="utf-8"))
    except (OSError,ValueError,TypeError):return {}

def fresh(value,now,minutes):
    try:
        t=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return bool(t.tzinfo) and 0<=(now-t.astimezone(UTC)).total_seconds()<=minutes*60
    except (ValueError,TypeError):return False

def plan(root=ROOT,now=None):
    now=now or dt.datetime.now(UTC)
    day=now.astimezone(ET).date().isoformat()
    yesterday=(now.astimezone(ET).date()-dt.timedelta(days=1)).isoformat()
    schedule=read(root,"docs/nba_schedule.json")
    health=read(root,"docs/ai_prizepicks_quick_join_health.json")
    pp=read(root,"docs/prizepicks_model_input.json")
    ai=read(root,"docs/ai_projection_fallback.json")
    horizon=read(root,"docs/nba_schedule_horizon_audit.json")
    grades=read(root,"docs/ai_forecast_grade_status.json")
    tasks=[]
    def add(file,reason):
        if file not in [x["workflow"] for x in tasks]:
            tasks.append({"workflow":file,"reason":reason})
    official_complete=(schedule.get("official_fixture_reconciliation",{})
        .get("verified_daily_counts",{}).get(day,{}).get("complete") is True)
    # The season master is verified independently; the current daily provider
    # need not repeat an additional manual official-count reference.
    day_horizon=(horizon.get("next_two_days_reconciliation") or {}).get(day) or {}
    today_rows=[g for g in schedule.get("games",[]) if isinstance(g,dict)
                and g.get("date_eastern")==day]
    season_complete=(
        horizon.get("status")=="READY"
        and fresh(horizon.get("checked_at"),now,480)
        and isinstance(day_horizon.get("season_fixed_games"),int)
        and day_horizon["season_fixed_games"]>0
        and day_horizon.get("daily_games")==day_horizon["season_fixed_games"]
        and len(today_rows)==day_horizon["daily_games"]
        and not day_horizon.get("missing"))
    schedule_complete=official_complete or season_complete
    if not fresh(schedule.get("generated_at"),now,180) or not schedule_complete:
        add("nba-schedule.yml","MISSING_OR_STALE_VERIFIED_SCHEDULE")
    # Full no-line forecast generation is independent of the PrizePicks
    # feed. Repair stale model estimates from real games without inventing
    # a market price, direction or hit probability.
    def upcoming_game(game):
        try:
            t=dt.datetime.fromisoformat(str(game.get("start","")).replace("Z","+00:00"))
            return bool(t.tzinfo) and now<t.astimezone(UTC)<=now+dt.timedelta(hours=36)
        except (ValueError,TypeError,OverflowError):
            return False
    upcoming=any(upcoming_game(g) for g in schedule.get("games",[]) if isinstance(g,dict))
    if upcoming and (not fresh(ai.get("generated_at"),now,120)
                     or ai.get("status")!="PREGAME_PROJECTIONS_NO_LINES"
                     or not ai.get("predictions")):
        add("nba-no-line-daily-projections.yml","UPCOMING_NBA_GAME_WITH_STALE_FREE_AI_PROJECTIONS")
    # Provider-free replay. No external provider billable request.
    if not fresh(health.get("generated_at"),now,90) or health.get("status")!="FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS":
        add("nba-prizepicks-site-publish.yml","STALE_OR_MISSING_FREE_COMPARISON_REPLAY")
    # Do not launch expensive model training for stale or nonexistent lines.
    genuine_lines=(pp.get("status")=="FRESH_AUTHENTIC_PRIZEPICKS_LINES"
        and pp.get("is_live") is True and bool(pp.get("picks"))
        and fresh(pp.get("generated_at") or pp.get("updated_at"),now,120))
    if genuine_lines and not fresh(health.get("model_generated_at"),now,180):
        add("nba-prizepicks-ai-board.yml","FRESH_LINES_WITH_STALE_AI")
    # Grading is also free: request independent final verification again.
    if (grades.get("game_date_eastern")==yesterday and
        int(grades.get("ungraded") or 0)>0 and
        not fresh(grades.get("generated_at"),now,45)):
        add("grade_frozen_ai_forecasts.yml","PREVIOUS_DAY_GRADES_UNRESOLVED")
    return {"checked_at":now.isoformat(),"date_eastern":day,
        "credit_spending_allowed":False,"dispatch_candidates":tasks,
        "stale_source_count":len(tasks),
        "grades_unresolved":grades.get("ungraded") if grades.get("game_date_eastern")==yesterday else None,
        "note":"Coordinator dispatches existing free-source workflows only; rate limiting and duplicate checks occur in GitHub Actions."}

if __name__=="__main__":
    print(json.dumps(plan(),indent=2))

"""Strict, free, read-only NBA production readiness gate.

Distinguish healthy, degraded, and unavailable feeds. Never infer uptime,
game observations, paid API credits, provider completeness, or picks.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/production_readiness.json"
ET=ZoneInfo("America/New_York")
MAX_AGE_MIN={"schedule":120,"ai_forecasts":120,"scoreboard":50,
             "prizepicks_lines":60,"nightly_grades":150}
FINAL_STATES={"post","final"}
PRE_STATES={"pre","scheduled"}

def parse_time(raw):
    try:
        t=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None
    except (TypeError,ValueError,OverflowError):
        return None

def check(now,files):
    if now.tzinfo is None:raise ValueError("Timezone-aware current time required")
    now=now.astimezone(dt.timezone.utc)
    day=now.astimezone(ET).date().isoformat()
    def load(name):
        data=files.get(name)
        return data if isinstance(data,dict) else {}
    schedule=load("nba_schedule.json")
    games=[g for g in schedule.get("games",[]) if isinstance(g,dict)]
    todays=[g for g in games if g.get("date_eastern")==day]
    upcoming=[g for g in todays if (t:=parse_time(g.get("start"))) and t>=now]
    started=[g for g in todays if (t:=parse_time(g.get("start"))) and t<now]
    # During NBA tipoff, scoreboard/boxscore cannot be treated as just optional.
    in_progress=[g for g in started if g.get("game_state") not in FINAL_STATES]
    next_tip=min((parse_time(g.get("start")) for g in upcoming),default=None)
    inputs={
        "schedule":(schedule,"generated_at"),
        "ai_forecasts":(load("ai_projection_fallback.json"),"generated_at"),
        "scoreboard":(load("nba_scoreboard_independent.json"),"generated_at"),
        "prizepicks_lines":(load("prizepicks_site.json"),"generated_at"),
        "nightly_grades":(load("nightly_grade_health.json"),"checked_at")
    }
    components={}
    def add(name,state,reasons,age=None,required=True):
        components[name]={"state":state,"required":required,
                          "reasons":reasons,"age_minutes":age}
    def age_of(obj,stamp):
        t=parse_time(obj.get(stamp))
        if t is None:return None
        return round((now-t).total_seconds()/60,1)
    def common(name):
        obj,stamp=inputs[name]
        age=age_of(obj,stamp)
        if age is None:return age,["MISSING_OR_INVALID_TIMESTAMP"]
        if age< -5:return age,["FUTURE_TIMESTAMP_INVALID"]
        if age>MAX_AGE_MIN[name]:return age,["STALE_SOURCE"]
        return age,[]
    age,issues=common("schedule")
    if schedule.get("coverage_complete") is not True:
        issues.append("SCHEDULE_NOT_COMPLETE")
    if not todays:
        issues.append("NO_TODAY_GAMES_IN_SCHEDULE")
    if schedule.get("total_games")!=len(games):
        issues.append("SCHEDULE_COUNT_MISMATCH")
    reference=load("verified_official_nba_fixtures.json")
    expected=(reference.get("official_expected_daily_counts") or {}).get(day)
    if isinstance(expected,int) and len(todays)!=expected:
        issues.append("OFFICIAL_NBA_SLATE_COUNT_MISMATCH")
    if isinstance(expected,int):
        official_keys={(g.get("away_abbreviation"),g.get("home_abbreviation"))
                       for g in reference.get("fixtures",[])
                       if g.get("date_eastern")==day}
        known_keys={(g.get("away_abbreviation"),g.get("home_abbreviation"))
                    for g in todays}
        if not official_keys.issubset(known_keys):
            issues.append("OFFICIAL_NBA_MATCHUP_MISSING")
    add("schedule","READY" if not issues else "BLOCKED",issues,age)

    ai=inputs["ai_forecasts"][0]
    age,issues=common("ai_forecasts")
    preds=ai.get("predictions",[])
    if ai.get("status")!="PREGAME_PROJECTIONS_NO_LINES" or not isinstance(preds,list) or not preds:
        issues.append("NO_VALID_AI_FORECAST_BOARD")
        preds=[]
    relevant={p.get("game") for p in preds if isinstance(p,dict) and
              p.get("is_pregame_prediction") is True and
              p.get("game") in {g.get("game") for g in upcoming}}
    missing={g.get("game") for g in upcoming}-relevant
    if missing:issues.append("UPCOMING_MATCHUPS_MISSING_AI")
    if schedule.get("coverage_complete") is not True:issues.append("SCHEDULE_DEPENDENCY_NOT_READY")
    add("ai_forecasts","READY" if not issues else "BLOCKED",issues,age,
        required=bool(upcoming))

    pp=inputs["prizepicks_lines"][0]
    age,issues=common("prizepicks_lines")
    if pp.get("status")!="LIVE_THIRD_PARTY_PRIZEPICKS_LINES":
        issues.append("NO_VALID_PRIZEPICKS_PROVIDER_DATA")
    offers=pp.get("board_offers")
    if not isinstance(offers,list) or not offers:
        issues.append("NO_OBSERVED_PRIZEPICKS_LINES")
        offers=[]
    if pp.get("complete_provider_board") is not True or pp.get("partial_board") is True:
        issues.append("PARTIAL_PRIZEPICKS_PROVIDER_COVERAGE")
    live_offers=[p for p in offers if isinstance(p,dict) and not p.get("is_demo") and
                 (t:=parse_time(p.get("starts_at"))) and t>now]
    if upcoming and not live_offers:issues.append("NO_UPCOMING_REAL_PROVIDER_LINES")
    add("prizepicks_lines","READY" if not issues else "DEGRADED",issues,age,
        required=bool(upcoming))

    # A fresh raw provider board and AI-only projections do NOT mean that
    # actual live prop cards were published. No recommendations may be inferred.
    published=load("data.json")
    comparisons=load("ai_comparisons.json")
    published_picks=published.get("picks")
    paired=comparisons.get("comparisons")
    picks_count=len(published_picks) if isinstance(published_picks,list) else 0
    pairs_count=len(paired) if isinstance(paired,list) else 0
    pick_latest=max((t for t in (
        parse_time(published.get("updated_at")),
        parse_time(comparisons.get("generated_at"))) if t is not None),default=None)
    pick_age=round((now-pick_latest).total_seconds()/60,1) if pick_latest else None
    pick_issues=[]
    if picks_count+pairs_count==0:
        pick_issues.append("NO_PUBLISHED_PROJECTION_VS_LINE_CARDS")
    if pick_age is None or pick_age>120 or pick_age< -5:
        pick_issues.append("PUBLISHED_PICK_BOARD_STALE")
    if published.get("slate_events_checked")==0 and upcoming:
        pick_issues.append("NO_PROVIDER_EVENTS_CHECKED")
    if published.get("market_coverage_limited") is True:
        pick_issues.append("SAVED_SPORTSBOOK_MARKET_COVERAGE_LIMITED")
    add("published_pick_cards","READY" if not pick_issues else "DEGRADED",
        pick_issues,pick_age,required=bool(upcoming))

    sb=inputs["scoreboard"][0]
    age,issues=common("scoreboard")
    if not isinstance(sb.get("games"),list) or not sb.get("games"):
        issues.append("NO_SCOREBOARD_GAMES")
    scoreboard_keys={(g.get("date_eastern"),g.get("away_abbreviation"),g.get("home_abbreviation"))
                     for g in (sb.get("games") or []) if isinstance(g,dict)}
    scheduled_keys={(g.get("date_eastern"),g.get("away_abbreviation"),g.get("home_abbreviation"))
                    for g in todays}
    if scheduled_keys-scoreboard_keys:
        issues.append("SCOREBOARD_MISSING_SCHEDULED_MATCHUPS")
    if in_progress and sb.get("is_live_score_source") is not True:
        issues.append("SCHEDULE_FALLBACK_NOT_LIVE_SCORES")
    if in_progress:
        observed={g.get("game"):g for g in sb.get("games",[]) if isinstance(g,dict)}
        for g in in_progress:
            v=observed.get(g.get("game"),{})
            if v.get("home_score") is None or v.get("away_score") is None:
                issues.append("IN_PROGRESS_GAME_MISSING_LIVE_SCORE")
                break
    add("scoreboard","READY" if not issues else "BLOCKED",list(dict.fromkeys(issues)),age,
        required=bool(todays))

    live=load("nba_player_tracking_independent.json")
    live_age=age_of(live,"captured_at")
    active=bool(in_progress)
    live_issues=[]
    if active:
        if live.get("status") not in ("OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
                                       "PARTIAL_NBA_PLAYER_BOXSCORES"):
            live_issues.append("NO_VERIFIED_LIVE_PLAYER_FEED")
        if live_age is None or live_age>30 or live_age< -5:
            live_issues.append("LIVE_PLAYER_DATA_STALE_OR_MISSING")
        tracked={g.get("game") for g in live.get("games",[]) if isinstance(g,dict)}
        if {g.get("game") for g in in_progress}-tracked:
            live_issues.append("ACTIVE_GAMES_MISSING_PLAYER_TOTALS")
    add("live_player_stats","READY" if not live_issues else "BLOCKED",live_issues,live_age,
        required=active)

    health=inputs["nightly_grades"][0]
    age,issues=common("nightly_grades")
    yesterday=(now.astimezone(ET).date()-dt.timedelta(days=1)).isoformat()
    if health.get("game_date_eastern")!=yesterday:
        issues.append("WRONG_GRADING_DATE")
    if health.get("prizepicks_overdue",0)>0 or health.get("paper_overdue",0)>0:
        issues.append("OVERDUE_GRADING")
    if health.get("capture_missing") is True:
        issues.append("PREVIOUS_DAY_MISSING_PAPER_AND_PRIZEPICKS_CAPTURES")
    if health.get("ai_forecasts_ungraded") not in (None,0):
        issues.append("PREVIOUS_DAY_AI_GRADING_INCOMPLETE")
    if health.get("ai_forecast_accuracy_status")=="AI_FORECAST_GRADE_REPORT_NOT_PUBLISHED_FOR_DAY":
        issues.append("MISSING_PREVIOUS_DAY_AI_GRADE_REPORT")
    add("nightly_grades","READY" if not issues else "DEGRADED",issues,age)
    blocked=[name for name,x in components.items() if x["required"] and x["state"]=="BLOCKED"]
    degraded=[name for name,x in components.items() if x["required"] and x["state"]=="DEGRADED"]
    overall="BLOCKED" if blocked else "DEGRADED" if degraded else "READY"
    return {
       "checked_at":now.isoformat(),"game_date_eastern":day,
       "status":overall,"ready_for_trustworthy_picks":overall=="READY",
       "readiness_is_not_model_accuracy":True,
       "today_schedule_games":len(todays),"upcoming_games":len(upcoming),
       "started_not_marked_final":len(in_progress),
       "next_tip_at":next_tip.isoformat() if next_tip else None,
       "components":components,"blocking_components":blocked,
       "degraded_components":degraded,
       "required_checks":sum(x["required"] for x in components.values()),
       "passing_required_checks":sum(x["required"] and x["state"]=="READY" for x in components.values()),
       "note":"Provider completeness, projection freshness, live score freshness, and grading health are independently checked. No guarantee of zero downtime, sportsbook coverage, predictive win rate, or actual API credit balance."
    }

def main():
    names=["nba_schedule.json","ai_projection_fallback.json",
           "nba_scoreboard_independent.json","prizepicks_site.json",
           "nightly_grade_health.json","nba_player_tracking_independent.json",
           "data.json","ai_comparisons.json","verified_official_nba_fixtures.json"]
    inputs={}
    for name in names:
        path=ROOT/"docs"/name
        try:
            inputs[name]=json.loads(path.read_text()) if path.exists() else {}
        except (OSError,ValueError):
            inputs[name]={}
    result=check(dt.datetime.now(dt.timezone.utc),inputs)
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print("PRODUCTION READINESS:",json.dumps({"status":result["status"],
         "passing":result["passing_required_checks"],"required":result["required_checks"],
         "blocked":result["blocking_components"],
         "degraded":result["degraded_components"]},sort_keys=True))
    if result["status"]!="READY":
        raise SystemExit(2)

if __name__=="__main__":
    main()

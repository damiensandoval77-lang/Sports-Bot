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

    # Published season is known long before betting lines appear. A missing
    # known fixture must fail production even if the provider lists no props.
    calendar=load("nba_schedule_horizon_audit.json")
    calendar_age=age_of(calendar,"checked_at")
    calendar_issues=[]
    if calendar.get("status")!="READY":
        calendar_issues.append("FULL_SEASON_CALENDAR_NOT_VERIFIED")
    if calendar_age is None or calendar_age< -5 or calendar_age>480:
        calendar_issues.append("SEASON_HORIZON_AUDIT_STALE")
    if calendar.get("season_fixed_games",0)<900:
        calendar_issues.append("SEASON_ARCHIVE_INCOMPLETE")
    horizon=calendar.get("next_14_days")
    if not isinstance(horizon,list) or len(horizon)!=14 or not horizon or horizon[0].get("date_eastern")!=day:
        calendar_issues.append("SEASON_HORIZON_WRONG_DATE_OR_LENGTH")
    current=calendar.get("next_two_days_reconciliation")
    if not isinstance(current,dict) or day not in current:
        calendar_issues.append("SEASON_DAILY_RECONCILIATION_UNAVAILABLE")
    elif current[day].get("missing"):
        calendar_issues.append("KNOWN_TODAY_GAMES_MISSING")
    add("season_calendar","READY" if not calendar_issues else "BLOCKED",
        calendar_issues,calendar_age,required=True)

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
    if pp.get("complete_provider_board") is True and pp.get("board_coverage_scope")!="NBA_ACTIVE_STANDARD_TIER_ONLY":
        issues.append("STANDARD_ONLY_PROVIDER_SCOPE_UNVERIFIED")
    live_offers=[p for p in offers if isinstance(p,dict) and not p.get("is_demo") and
                 (t:=parse_time(p.get("starts_at"))) and t>now]
    if upcoming and not live_offers:issues.append("NO_UPCOMING_REAL_PROVIDER_LINES")
    # A board can be fresh and nonempty while an entire scheduled matchup has
    # zero actual standard lines. Never let one game's offers mask another.
    live_games={p.get("game") for p in live_offers if
                p.get("more_tier") in (None,"standard") and
                p.get("less_tier") in (None,"standard")}
    missing_provider_games=sorted({g.get("game") for g in upcoming
                                   if g.get("game") not in live_games})
    if missing_provider_games:
        issues.append("UPCOMING_MATCHUPS_WITHOUT_STANDARD_PROVIDER_LINES")
    add("prizepicks_lines","READY" if not issues else "DEGRADED",issues,age,
        required=bool(upcoming))

    # Gradeability is defined by what the unified app ACTUALLY publishes:
    # authentic, immutable pretip standard-line picks. Raw sportsbook quotes
    # without safe models remain diagnostic only and never become picks.
    capture=load("tonight_capture_gradeability.json")
    capture_age=age_of(capture,"checked_at")
    capture_issues=[]
    coverage_issues=[]
    summary=capture.get("summary") if isinstance(capture.get("summary"),dict) else {}
    if capture.get("game_date_eastern")!=day:
        capture_issues.append("CAPTURE_REPORT_WRONG_SLATE_DATE")
    if capture_age is None or capture_age< -5 or capture_age>90:
        capture_issues.append("CAPTURE_REPORT_STALE")
    if upcoming:
        if capture.get("status") not in ("CAPTURE_VERIFIED","CAPTURE_INCOMPLETE"):
            capture_issues.append("CAPTURE_INPUTS_NOT_VERIFIED")
        # Incomplete source-to-model coverage is different from invalid or
        # missing grades for already published model picks.
        allowed_raw_gap="STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"
        rows=capture.get("games")
        if not isinstance(rows,list) or len(rows)!=len(todays):
            capture_issues.append("CAPTURE_PER_GAME_RECONCILIATION_UNAVAILABLE")
        else:
            expected_games={g.get("game") for g in todays}
            reported_games=[r.get("game") for r in rows if isinstance(r,dict)]
            if set(reported_games)!=expected_games or len(reported_games)!=len(rows):
                capture_issues.append("CAPTURE_GAME_IDENTITY_MISMATCH")
            for row in rows:
                if not isinstance(row,dict) or not isinstance(row.get("issues"),list):
                    capture_issues.append("CAPTURE_GAME_RECORD_INVALID")
                    continue
                if any(issue!=allowed_raw_gap for issue in row["issues"]):
                    capture_issues.append("REQUIRED_PREGAME_PICK_ARTIFACT_MISSING")
        if summary.get("schedule_games")!=len(todays):
            capture_issues.append("CAPTURE_SCHEDULE_COUNT_MISMATCH")
        if summary.get("games_with_saved_source_quotes",0)<len(upcoming):
            capture_issues.append("UPCOMING_GAMES_WITHOUT_FROZEN_QUOTES")
        if summary.get("games_with_frozen_ai",0)<len(upcoming):
            capture_issues.append("UPCOMING_GAMES_WITHOUT_FROZEN_AI")
        if summary.get("games_with_line_backed_models",0)<len(upcoming):
            capture_issues.append("UPCOMING_GAMES_WITHOUT_GRADEABLE_SAVED_PICKS")
        missing=summary.get("total_standard_markets_without_frozen_model")
        fallback=summary.get("total_missing_primary_with_separate_research_receipt")
        no_ai=summary.get("total_missing_primary_without_any_ai_receipt")
        if any(type(x) is not int or x<0 for x in (missing,fallback,no_ai)) or missing!=fallback+no_ai:
            capture_issues.append("CAPTURE_RECONCILIATION_INCONSISTENT")
        elif missing>0:
            coverage_issues.append("STANDARD_QUOTES_WITHOUT_PRIMARY_FROZEN_MODEL")
        if summary.get("total_standard_source_quotes",0)==0:
            capture_issues.append("NO_ARCHIVED_STANDARD_QUOTES")
        if summary.get("total_line_backed",0)<len(upcoming):
            capture_issues.append("NO_GRADEABLE_FROZEN_PICKS_FOR_EVERY_UPCOMING_GAME")
    add("pregame_capture","READY" if not capture_issues else "DEGRADED",
        list(dict.fromkeys(capture_issues)),capture_age,required=bool(upcoming))
    add("unmodeled_provider_market_coverage",
        "READY" if not coverage_issues else "DEGRADED",
        coverage_issues,capture_age,required=False)
    current=capture.get("current_upcoming_coverage")
    current_issues=[]
    if upcoming:
        if not isinstance(current,dict) or current.get("status") not in ("COMPLETE","INCOMPLETE"):
            current_issues.append("CURRENT_STANDARD_MODEL_COVERAGE_UNVERIFIED")
        else:
            missing=current.get("missing_primary_offers")
            rows=current.get("games")
            # Report timestamps may use equivalent +00:00 versus Z syntax.
            def identity(game):
                return (game.get("game"),parse_time(game.get("start")))
            expected={identity(g) for g in upcoming}
            actual={identity(g) for g in rows if isinstance(g,dict)} if isinstance(rows,list) else set()
            valid_counts=isinstance(rows,list) and all(isinstance(g,dict) and all(
                type(g.get(k)) is int and g[k]>=0 for k in
                ("verified_current_offers","matched_primary_offers","missing_primary_offers")) and
                g["verified_current_offers"]==g["matched_primary_offers"]+g["missing_primary_offers"]
                for g in rows)
            if (type(missing) is not int or missing<0 or actual!=expected or not valid_counts or
                missing!=sum(g["missing_primary_offers"] for g in rows)):
                current_issues.append("CURRENT_STANDARD_MODEL_COVERAGE_INVALID")
            elif missing>0:
                current_issues.append("CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL")
            if current.get("issues") or current.get("status")!="COMPLETE":
                current_issues.append("CURRENT_STANDARD_MODEL_COVERAGE_INCOMPLETE")
        if capture_age is None or capture_age< -5 or capture_age>90:
            current_issues.append("CURRENT_STANDARD_MODEL_COVERAGE_STALE")
    add("current_primary_model_coverage","DEGRADED" if current_issues else "READY",
        current_issues,capture_age,required=bool(upcoming))
    # This is the actual grade/void pipeline health of EVERY advertised pick.
    settled=load("dames-picks/published_pick_settlement.json")
    settlement_age=age_of(settled,"checked_at")
    settlement_issues=[]
    if settlement_age is None or settlement_age< -5 or settlement_age>65:
        settlement_issues.append("PUBLISHED_GRADEABILITY_AUDIT_STALE")
    if settled.get("status")!="READY":
        settlement_issues.append("PUBLISHED_FROZEN_PICKS_NOT_GRADEABLE")
    counts=settled.get("counts") if isinstance(settled.get("counts"),dict) else {}
    if not isinstance(counts.get("frozen_picks"),int) or counts["frozen_picks"]<1:
        settlement_issues.append("NO_VERIFIED_PUBLISHED_FROZEN_PICKS")
    add("published_pick_settlement","READY" if not settlement_issues else "DEGRADED",
        settlement_issues,settlement_age,required=True)

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
    # Legacy American-odds sportsbook cards are optional for the
    # PrizePicks-first dashboard. They remain separately audited and visibly
    # degraded, but must not be confused with the authenticated pick'em board.
    # The actual PrizePicks cards are independently required and verified by
    # the public_browser gate, including real standard lines and model chances.
    add("published_pick_cards","READY" if not pick_issues else "DEGRADED",
        pick_issues,pick_age,required=False)

    # Distinguish the newly published PrizePicks research-only dashboard fallback
    # from the legacy paid sportsbook market card readiness above.
    # Snapshot existence is NOT proof a browser deployed or rendered the cards.
    quick=load("ai_prizepicks_quick_join_health.json")
    quick_age=age_of(quick,"generated_at")
    quick_issues=[]
    if quick.get("status")!="FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS" or quick.get("research_only") is not True:
        quick_issues.append("NO_PUBLISHED_VERIFIED_PP_RESEARCH_JOIN")
    if quick_age is None or quick_age< -5 or quick_age>90:
        quick_issues.append("PP_RESEARCH_JOIN_STALE")
    if (t:=parse_time(quick.get("provider_generated_at"))) is None or not 0<=(now-t).total_seconds()<=90*60:
        quick_issues.append("PP_RESEARCH_PROVIDER_SOURCE_STALE")
    if not isinstance(quick.get("offers_matched"),int) or quick.get("offers_matched",0)<=0:
        quick_issues.append("NO_MATCHED_PP_RESEARCH_OFFERS")
    match_counts=quick.get("matched_by_game") or {}
    if not isinstance(match_counts,dict):
        match_counts={}
    if upcoming and any(match_counts.get(g.get("game"),0)<=0 for g in upcoming):
        quick_issues.append("UPCOMING_GAMES_WITHOUT_PP_RESEARCH_MATCHES")
    html=files.get("dashboard_html", "")
    if not isinstance(html,str) or 'fetchJSON("ai_prizepicks_quick_join.json")' not in html or "verifiedPublishedPrizePicksJoins(" not in html:
        quick_issues.append("DASHBOARD_PP_JOIN_HANDOFF_NOT_PRESENT")
    if quick.get("partial_provider_board") is True or quick.get("source_coverage_complete") is not True:
        quick_issues.append("PP_RESEARCH_SOURCE_PARTIAL")
    add("prizepicks_research_cards","READY" if not quick_issues else "DEGRADED",
        quick_issues,quick_age,required=False)

    # The only user-facing app is /dames-picks/. Legacy docs/index.html
    # redirects and its old #ai-board probe cannot certify that NBA+NFL
    # renders successfully. Keep current slate quote/freeze checks separate.
    browser=load("dames-picks/browser_readiness.json")
    browser_age=age_of(browser,"checked_at")
    browser_issues=[]
    if browser.get("status")!="READY" or browser.get("browser_render_verified") is not True:
        browser_issues.append("UNIFIED_BROWSER_NOT_VERIFIED")
    if browser_age is None or browser_age< -5 or browser_age>90:
        browser_issues.append("UNIFIED_BROWSER_PROBE_STALE")
    if not str(browser.get("site_url","")).rstrip("/").endswith("/Sports-Bot/dames-picks"):
        browser_issues.append("PUBLIC_SITE_NOT_UNIFIED_APP")
    if "NBA + NFL" not in str(browser.get("app_title","")):
        browser_issues.append("UNIFIED_APP_TITLE_MISSING")
    for sport in ("NBA","NFL"):
        observation=browser.get(sport)
        if not isinstance(observation,dict):
            browser_issues.append(sport+"_PUBLIC_FEED_UNVERIFIED")
            continue
        if observation.get("selected")!=sport or observation.get("loaded") is not True:
            browser_issues.append(sport+"_PUBLIC_FEED_NOT_LOADED")
        if not isinstance(observation.get("rows"),int) or observation["rows"]<1:
            browser_issues.append(sport+"_NO_SAVED_PROPS_RENDERED")
        if not isinstance(observation.get("rendered"),int) or observation["rendered"]<1:
            browser_issues.append(sport+"_PUBLIC_CARDS_NOT_RENDERED")
        if sport=="NFL" and any("NFL feed partially loaded" in str(err) or
                              "NFL export unavailable" in str(err) for err in observation.get("errors",[])):
            browser_issues.append("NFL_PUBLIC_EXPORT_PARTIAL")
    add("public_browser","READY" if not browser_issues else "DEGRADED",
        browser_issues,browser_age,required=bool(todays))

    sb=inputs["scoreboard"][0]
    age,issues=common("scoreboard")
    if not isinstance(sb.get("games"),list) or not sb.get("games"):
        issues.append("NO_SCOREBOARD_GAMES")
    def canonical_team(value):
        return {"WSH":"WAS", "GS":"GSW", "NY":"NYK", "NO":"NOP", "SA":"SAS", "UTAH":"UTA"}.get(value,value)
    scoreboard_keys={(g.get("date_eastern"),canonical_team(g.get("away_abbreviation")),canonical_team(g.get("home_abbreviation")))
                     for g in (sb.get("games") or []) if isinstance(g,dict)}
    scheduled_keys={(g.get("date_eastern"),canonical_team(g.get("away_abbreviation")),canonical_team(g.get("home_abbreviation")))
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
    fallback=load("live_player_tracking.json")
    live_age=age_of(live,"captured_at")
    active=bool(in_progress)
    live_issues=[]
    if active:
        tracked=set()
        valid_source=False
        fresh_source=False
        if live.get("status") in ("OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
                                  "PARTIAL_NBA_PLAYER_BOXSCORES"):
            valid_source=True
            if live_age is not None and -5<=live_age<=30:
                fresh_source=True
                tracked.update(g.get("game") for g in live.get("games",[]) if isinstance(g,dict))
        fallback_age=age_of(fallback,"captured_at")
        if (fallback.get("status")=="OBSERVED_ESPN_LIVE_BOX_SCORES_SERVER_FALLBACK"
                and fallback.get("date_eastern")==day
                and fallback.get("player_totals_are_observations") is True):
            valid_source=True
            if fallback_age is not None and 0<=fallback_age<=5:
                fresh_source=True
                for game in fallback.get("games",[]):
                    if not isinstance(game,dict):continue
                    observed=parse_time(game.get("observed_at"))
                    seconds=(now-observed).total_seconds() if observed else None
                    if (game.get("state") in ("in","post") and game.get("stale") is False
                            and str(game.get("event_id","")).isdecimal()
                            and isinstance(game.get("player_rows"),list) and game["player_rows"]
                            and seconds is not None and 0<=seconds<=300):
                        tracked.add(game.get("game"))
                live_age=min(live_age,fallback_age) if live_age is not None else fallback_age
        if not valid_source:live_issues.append("NO_VERIFIED_LIVE_PLAYER_FEED")
        if not fresh_source:live_issues.append("LIVE_PLAYER_DATA_STALE_OR_MISSING")
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
           "nightly_grade_health.json","nba_player_tracking_independent.json","live_player_tracking.json",
           "data.json","ai_comparisons.json","verified_official_nba_fixtures.json",
           "ai_prizepicks_quick_join_health.json",
           "tonight_capture_gradeability.json","dames-picks/browser_readiness.json",
           "dames-picks/published_pick_settlement.json",
           "nba_schedule_horizon_audit.json"]
    inputs={}
    for name in names:
        path=ROOT/"docs"/name
        try:
            inputs[name]=json.loads(path.read_text()) if path.exists() else {}
        except (OSError,ValueError):
            inputs[name]={}
    try:
        inputs["dashboard_html"]=(ROOT/"docs/dames-picks/index.html").read_text()
    except OSError:
        inputs["dashboard_html"]=""
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

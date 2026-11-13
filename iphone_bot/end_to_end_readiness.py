#!/usr/bin/env python3
"""Fail-closed, zero-provider-cost cross-check of published pregame and grade snapshots."""
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc

def parse_time(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    except (TypeError, AttributeError, ValueError):
        return None

def age_ok(value, now, minutes):
    parsed = parse_time(value)
    return parsed is not None and 0 <= (now - parsed).total_seconds() <= minutes * 60

def evaluate(schedule, health, production, grades, now=None, season=None, capture=None):
    now = now or dt.datetime.now(UTC)
    day = now.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    games = [g for g in schedule.get("games", []) if g.get("date_eastern") == day]
    names = {g.get("game") for g in games if g.get("game")}
    official = schedule.get("official_fixture_reconciliation", {}).get("verified_daily_counts", {}).get(day, {})
    reference = "MANUALLY_VERIFIED_DAILY_COUNT"
    # The old manual Nov 9 fixture supplement is not the season calendar.
    # Validate actual matchup identities against the independently published
    # full-season archive when a manually verified daily count is absent.
    if not official and season:
        try:
            from iphone_bot.season_schedule_baseline import validate
            validate(season)
            expected = [g for g in season["games"] if g["date_eastern"] == day]
            identity = lambda g: (g.get("away_abbreviation"),g.get("home_abbreviation"),g.get("start"))
            official = {"official_expected":len(expected),
                        "complete":{identity(g) for g in expected}=={identity(g) for g in games}}
            reference = "VALIDATED_PUBLISHED_SEASON_BASELINE"
        except (ValueError,KeyError,TypeError):
            reference = "INVALID_SEASON_BASELINE"
    upcoming = {g.get("game") for g in games if g.get("game") and
                (parse_time(g.get("start")) is None or parse_time(g.get("start")) > now)}
    matched = health.get("matched_by_game", {})
    observed = {game: int(matched.get(game, 0)) for game in names}
    failures = []
    def require(test, reason):
        if not test:
            failures.append(reason)
    require(bool(official.get("complete")) and official.get("official_expected") == len(names)
            and len(games) == len(names), "INCOMPLETE_VERIFIED_SLATE")
    require(age_ok(schedule.get("generated_at"), now, 180), "STALE_SCHEDULE")
    if upcoming:
        require(age_ok(health.get("generated_at"), now, 90), "STALE_COMPARISON_REPORT")
        require(age_ok(health.get("provider_generated_at"), now, 90), "STALE_PRIZEPICKS_SOURCE")
        require(age_ok(health.get("model_generated_at"), now, 180), "STALE_AI_MODEL")
        require(health.get("status") == "FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
                "NO_FRESH_VERIFIED_COMPARISONS")
        require(all(observed[name] > 0 for name in upcoming), "GAMES_WITHOUT_VERIFIED_COMPARISONS")
        require(not health.get("partial_provider_board") and health.get("source_coverage_complete") is True,
                "PARTIAL_PRIZEPICKS_BOARD")
    started = names - upcoming
    if started:
        capture = capture or {}
        require(capture.get("game_date_eastern") == day and age_ok(capture.get("checked_at"),now,60),
                "STALE_OR_MISSING_CAPTURE_AUDIT")
        archived = {g.get("game"):g for g in capture.get("games",[])}
        require(all(name in archived and archived[name].get("frozen_line_backed",0)>0
                    for name in started), "STARTED_GAMES_WITHOUT_FROZEN_MODELS")
        require(all(name in archived and archived[name].get("standard_markets_without_frozen_model") == 0
                    for name in started), "ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL")
    require(production.get("game_date_eastern") == day and age_ok(production.get("checked_at"), now, 60),
            "STALE_PRODUCTION_GATE")
    require(production.get("ready_for_trustworthy_picks") is True, "PUBLISHED_PICK_BOARD_NOT_READY")
    previous_day = (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()
    require(grades.get("game_date_eastern") == previous_day, "PREVIOUS_DAY_GRADE_STATUS_MISSING")
    require(age_ok(grades.get("generated_at"), now, 180), "STALE_GRADE_STATUS")
    require(grades.get("ungraded") == 0 and grades.get("recorded_pregame_forecasts", 0) > 0,
            "PREVIOUS_DAY_FORECASTS_UNGRADED")
    return {
        "checked_at": now.isoformat(), "date_eastern": day,
        "status": "READY" if not failures else "DEGRADED",
        "verified_slate_games": len(names), "official_expected_games": official.get("official_expected"),
        "slate_reference":reference,"upcoming_games":len(upcoming),"started_games":len(started),
        "games_with_matching_offers": sum(v > 0 for v in observed.values()),
        "matched_offers_today": sum(observed.values()),
        "matches_by_today_game": dict(sorted(observed.items())),
        "other_day_game_labels": sorted(set(matched) - names),
        "research_only_not_actionable": health.get("research_only", True),
        "failures": failures,
        "note": "Snapshot readiness only. No live API calls, no credit use, and no claim about betting accuracy."
    }

def load(path):
    try:
        return json.loads((ROOT / path).read_text())
    except (OSError, ValueError):
        return {}

def main():
    report = evaluate(load("docs/nba_schedule.json"),
                      load("docs/ai_prizepicks_quick_join_health.json"),
                      load("docs/production_readiness.json"),
                      load("docs/ai_forecast_grade_status.json"),
                      season=load("docs/nba_season_schedule_2026_27.json"),
                      capture=load("docs/tonight_capture_gradeability.json"))
    out=ROOT/"out/end-to-end-readiness.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report, indent=2))
    if report["status"] != "READY":
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Independent, public NBA scoreboard snapshot; no paid API or Replit required.

Snapshots are labeled as schedule/score observations, never sportsbook lines.
On an upstream failure we retain the last good snapshot rather than replacing
it with an empty one falsely marked fresh.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from iphone_bot.fetch_nba_schedule import collect, read_schedule, nba_season_schedule, parse_nba_game, request_json
from iphone_bot.official_game_id_index import update_index

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/nba_scoreboard_independent.json"
EASTERN = ZoneInfo("America/New_York")
NBA_LIVE_URLS = (
    "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
    "https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData/scoreboard/todaysScoreboard_00.json",
)

def nba_live_scoreboard(days, requester=request_json, validate_rows=None):
    """Fetch live NBA scoreboard via CDN or original mediaops S3 source."""
    failures = []
    for url in NBA_LIVE_URLS:
        try:
            result = requester(url)
            scoreboard = result["scoreboard"]
            raw = scoreboard["games"]
            if not isinstance(raw, list):
                raise ValueError("NBA live games missing")
            rows = []
            seen = set()
            for game in raw:
                parsed = parse_nba_game(game, set(days))
                if parsed is not None and parsed["id"] not in seen:
                    seen.add(parsed["id"])
                    rows.append(parsed)
            if validate_rows is not None and not validate_rows(rows):
                raise ValueError("Incomplete or stale live scoreboard; try next endpoint")
            return {"events": sorted(rows, key=lambda g:g["start"]),
                    "source": "NBA official liveData scoreboard via "+
                              ("NBA CDN" if url == NBA_LIVE_URLS[0] else "mediaops S3"),
                    "rejected": len(raw)-len(rows)}
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, TimeoutError) as e:
            failures.append(type(e).__name__)
    raise RuntimeError("All NBA live scoreboard endpoints failed: "+", ".join(failures))


def expected_matchups(schedule, days):
    """Only trust an explicitly complete schedule for the same requested dates."""
    if not isinstance(schedule, dict) or schedule.get("coverage_complete") is not True:
        return set()
    requested = {d.isoformat() for d in days}
    covered_dates = set(schedule.get("dates_eastern") or [])
    if not requested.issubset(covered_dates):
        return set()
    return {(str(g.get("date_eastern")), str(g.get("game", "")).strip().casefold())
            for g in schedule.get("games", [])
            if g.get("date_eastern") in requested and g.get("game")}

def started_games_missing_scores(rows, schedule, days, now, grace_minutes=10):
    """Do not treat an all-pregame schedule as live after verified tipoff.

    The fixture start is only a signal to re-query an independent source,
    never permission to invent a score or assume play is underway.
    """
    if not isinstance(schedule,dict) or schedule.get("coverage_complete") is not True:
        return False
    requested={d.isoformat() for d in days}
    if not requested.issubset(set(schedule.get("dates_eastern") or [])):
        return False
    observed={(g.get("date_eastern"),g.get("game")):g
              for g in rows if isinstance(g,dict)}
    for game in schedule.get("games",[]):
        if not isinstance(game,dict) or game.get("date_eastern") not in requested:
            continue
        try:
            tip=dt.datetime.fromisoformat(str(game["start"]).replace("Z","+00:00"))
            if tip.tzinfo is None or now < tip.astimezone(dt.timezone.utc)+dt.timedelta(minutes=grace_minutes):
                continue
        except (KeyError,ValueError,TypeError):
            continue
        observed_game=observed.get((game.get("date_eastern"),game.get("game")),{})
        if (observed_game.get("game_state")=="pre" or
            observed_game.get("home_score") is None or
            observed_game.get("away_score") is None):
            return True
    return False

def snapshot(days, reader=read_schedule, now=None, previous=None, schedule=None, fallback=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    dates = [d.isoformat() for d in days]
    try:
        try:
            report = collect(days, reader=reader)
            rows = report.get("games", [])
            expected = expected_matchups(schedule, days)
            primary_matchups={(str(g.get("date_eastern")),str(g.get("game","")).strip().casefold())
                              for g in rows if g.get("game")}
            if expected and not expected.issubset(primary_matchups):
                # ESPN returned HTTP 200, but dropped one or more verified
                # NBA fixtures; do not let that masquerade as full coverage.
                raise ValueError("Incomplete ESPN slate; invoke independent NBA fallback")
            if started_games_missing_scores(rows,schedule,days,now):
                raise ValueError("ESPN returned stale pretip schedule after official game start")
            source = "ESPN public scoreboard (not sportsbook or player prop data)"
            status = "OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES"
        except (OSError, TimeoutError, RuntimeError, ValueError, KeyError, TypeError) as primary_error:
            if fallback is None:
                raise
            backup = fallback(days)
            if not isinstance(backup, dict) or not isinstance(backup.get("events"), list):
                raise ValueError("Malformed independent NBA schedule fallback")
            rows = backup["events"]
            report = {"source_records_rejected": backup.get("rejected", 0)}
            source = backup.get("source") or "NBA public CDN season schedule"
            status = ("OBSERVED_NBA_LIVE_SCOREBOARD" if source.startswith("NBA official liveData")
                      else "NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE")
        if not isinstance(rows, list):
            raise ValueError("Scoreboard games must be a list")
        if started_games_missing_scores(rows,schedule,days,now):
            raise ValueError("No live scoreboard scores after scheduled tipoff on any validated source")
        expected = expected_matchups(schedule, days)
        observed = {(str(g.get("date_eastern")), str(g.get("game", "")).strip().casefold())
                    for g in rows if g.get("game")}
        if expected and not expected.issubset(observed):
            raise ValueError("Incomplete scoreboard response relative to verified scheduled slate")
        if len(dates) != len(set(dates)):
            raise ValueError("Duplicate requested dates")
        if len({str(g.get("id")) for g in rows}) != len(rows):
            raise ValueError("Duplicate game identifiers")
        return {
            "generated_at": now.isoformat(),
            "status": status,
            "source": source,
            "is_live_score_source": status in ("OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES","OBSERVED_NBA_LIVE_SCOREBOARD"),
            "dates_eastern": dates,
            "total_games": len(rows),
            "games": rows,
            "source_records_rejected": report.get("source_records_rejected", 0),
            "is_sportsbook_feed": False,
            "is_prizepicks_feed": False,
            "error": None,
        }
    except (OSError, TimeoutError, RuntimeError, ValueError, KeyError, TypeError) as e:
        # A stale snapshot remains stale; do not update its generated_at field.
        old = dict(previous or {})
        if old.get("games") and old.get("generated_at"):
            old["status"] = "STALE_UPSTREAM_ERROR"
            old["last_attempt_at"] = now.isoformat()
            old["error"] = type(e).__name__
            return old
        return {
            "generated_at": None,
            "last_attempt_at": now.isoformat(),
            "status": "UNAVAILABLE_UPSTREAM_ERROR",
            "source": "ESPN public scoreboard (not sportsbook)",
            "dates_eastern": dates,
            "total_games": 0,
            "games": [],
            "error": type(e).__name__,
            "is_sportsbook_feed": False,
            "is_prizepicks_feed": False,
        }

def main():
    day=dt.datetime.now(EASTERN).date()
    days=[day]
    previous = None
    if OUTPUT.exists():
        try:
            previous=json.loads(OUTPUT.read_text())
        except (OSError,ValueError):
            pass
    baseline = None
    baseline_path = ROOT / "docs/nba_schedule.json"
    if baseline_path.exists():
        try:
            baseline = json.loads(baseline_path.read_text())
        except (OSError, ValueError):
            pass
    def alternative(dates):
        expected = expected_matchups(baseline, dates)
        try:
            def valid_live_rows(rows):
                actual={(str(g.get("date_eastern")),str(g.get("game","")).strip().casefold())
                        for g in rows}
                return ((not expected or expected.issubset(actual)) and
                        not started_games_missing_scores(rows,baseline,dates,
                                                         dt.datetime.now(dt.timezone.utc)))
            observed = nba_live_scoreboard(dates, validate_rows=valid_live_rows)
            actual = {(str(g.get("date_eastern")), str(g.get("game", "")).strip().casefold())
                      for g in observed["events"]}
            # NBA liveData can still carry yesterday's games before its date rollover.
            # Do not report an empty/previous-day result as today's live scoreboard.
            if not expected or expected.issubset(actual):
                return observed
        except RuntimeError:
            pass
        try:
            season=nba_season_schedule(dates)
            season_matchups={(str(g.get("date_eastern")),str(g.get("game","")).strip().casefold())
                             for g in season.get("events",[]) if g.get("game")}
            if expected and not expected.issubset(season_matchups):
                raise RuntimeError("NBA season schedule omitted officially verified game")
            return season
        except (RuntimeError,ValueError):
            # Last resort: a separately validated existing dated schedule.
            # This is useful for matchup tabs but never a fresh LIVE scoreboard.
            if expected and baseline and baseline.get("coverage_complete") is True:
                rows = [dict(g) for g in baseline.get("games", [])
                        if g.get("date_eastern") in {d.isoformat() for d in dates}]
                for row in rows:
                    row["away_score"] = None
                    row["home_score"] = None
                    if row.get("game_state") == "in":
                        row["game_state"] = "unknown"
                return {"events": rows,
                        "source": "Previously verified NBA schedule cache (NOT live scores)",
                        "rejected": 0}
            raise
    result=snapshot(days,previous=previous,schedule=baseline,fallback=alternative)
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    # Game IDs come only from observed official NBA liveData, not ESPN IDs or
    # third-party schedule guesses. Preserve them across daily rollover.
    known=update_index(ROOT/"docs/official_nba_game_ids.json",result)
    print("Saved verified official NBA game IDs:",known)
    print(json.dumps({"status":result["status"],"total_games":result["total_games"],
                      "generated_at":result["generated_at"],"error":result.get("error")}))
    if result["status"] not in ("OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES", "OBSERVED_NBA_LIVE_SCOREBOARD", "NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE"):
        raise SystemExit(1)

if __name__=="__main__":
    main()

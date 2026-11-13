#!/usr/bin/env python3
"""Capture NBA liveData player box scores with explicit source and freshness.

This free public-data research feed does not infer betting lines, model
projections or player availability. Empty pregame slates aren't live stats.
"""
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

from iphone_bot.fetch_nba_schedule import parse_nba_game, request_json
from iphone_bot.refresh_independent_scoreboard import NBA_LIVE_URLS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/nba_player_tracking_independent.json"
EASTERN = ZoneInfo("America/New_York")
BOX_BASES = (
    "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_",
    "https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData/boxscore/boxscore_",
)

SOURCE_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError)


def collect_game_boxscore(raw, parsed, fetch, now):
    gid = str(raw.get("gameId") or "")
    if not gid.isdigit() or len(gid) != 10:
        return None, ["INVALID_GAME_ID"]

    failures = []
    for prefix in BOX_BASES:
        try:
            box = fetch(prefix + gid + ".json")["game"]
            if str(box.get("gameId")) != gid:
                raise ValueError("Boxscore/game id mismatch")
            rows = []
            for kind in ("awayTeam", "homeTeam"):
                team = box[kind]
                tricode = team["teamTricode"]
                if not tricode or tricode != raw[kind]["teamTricode"]:
                    raise ValueError("Boxscore team mismatch")
                team_rows = []
                for player in team.get("players") or []:
                    stats = player.get("statistics") or {}
                    pid = player.get("personId")
                    if not pid or not player.get("name"):
                        continue
                    vals = (stats.get("points"), stats.get("reboundsTotal"), stats.get("assists"))
                    if any(type(n) not in (int, float) or n < 0 for n in vals):
                        continue
                    pts, reb, ast = vals
                    team_rows.append({"player": player["name"], "player_id": str(pid), "team": tricode,
                                      "PTS": pts, "REB": reb, "AST": ast, "PRA": pts + reb + ast})
                if not team_rows:
                    raise ValueError("Empty team player boxscore")
                rows.extend(team_rows)
            return {"game": parsed["game"], "id": parsed["id"],
                    "state": parsed["game_state"], "period": parsed.get("period"),
                    "shortDetail": raw.get("gameStatusText"), "clock": raw.get("gameClock"),
                    "observed_at": now.isoformat(), "player_rows": rows}, failures
        except SOURCE_ERRORS as err:
            failures.append(f"BOXSCORE_{gid}_{type(err).__name__}: {err}")
    return None, failures


def collect_boxscores(day, fetch=request_json, now=None, max_games=15):
    now = now or dt.datetime.now(dt.timezone.utc)
    if not (1 <= max_games <= 15):
        raise ValueError("max_games must be between 1 and 15")
    failures = []
    for url in NBA_LIVE_URLS:
        try:
            scoreboard = fetch(url)["scoreboard"]
            raw_games = scoreboard["games"]
            if not isinstance(raw_games, list):
                raise ValueError("Malformed liveData scoreboard")
            if scoreboard.get("gameDate") and scoreboard["gameDate"] != day.isoformat():
                raise ValueError("NBA liveData scoreboard has not rolled to the requested Eastern date")
            break
        except SOURCE_ERRORS as err:
            failures.append(str(err))
    else:
        raise ValueError("NBA liveData scoreboard unavailable: " + "; ".join(failures))

    active = []
    for raw in raw_games:
        parsed = parse_nba_game(raw, {day})
        if parsed and parsed["game_state"] in ("in", "post"):
            active.append((raw, parsed))
    count_active = len(active)
    if count_active > max_games:
        raise ValueError("Active game limit exceeded; cannot claim full coverage")

    games = []
    if active:
        # Bound concurrent requests so one stalled fixture does not consume
        # the workflow deadline or suppress independent verified boxes.
        with ThreadPoolExecutor(max_workers=min(5, count_active)) as pool:
            pending = [pool.submit(collect_game_boxscore, raw, parsed, fetch, now)
                       for raw, parsed in active]
            for future in pending:
                observation, errors = future.result()
                failures.extend(errors)
                if observation is not None:
                    games.append(observation)
    complete = len(games) == count_active
    return {"status": ("OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES"
                       if complete else "PARTIAL_NBA_PLAYER_BOXSCORES"),
            "captured_at": now.isoformat(), "date_eastern": day.isoformat(),
            "source": "NBA public liveData scoreboard and game boxscore",
            "games": games, "errors": failures,
            "coverage": {"observed_game_count": len(games),
                         "active_or_final_count": count_active,
                         "complete": complete},
            "not_sportsbook_lines": True, "not_ai_projections": True}

def waiting_for_tipoff(schedule, day, now=None):
    """No live boxscore is expected before the first independently scheduled tip."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(schedule, dict) or schedule.get("coverage_complete") is not True:
        return None
    if day.isoformat() not in (schedule.get("dates_eastern") or []):
        return None
    games = [g for g in schedule.get("games", [])
             if g.get("date_eastern") == day.isoformat()]
    if not games:
        return None
    starts = []
    for g in games:
        try:
            stamp = dt.datetime.fromisoformat(str(g["start"]).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                return None
            starts.append(stamp.astimezone(dt.timezone.utc))
        except (KeyError, ValueError, TypeError):
            return None
    next_tip = min(starts)
    if now >= next_tip:
        return None
    return {
        "status": "WAITING_FOR_SCHEDULED_TIPOFF",
        "captured_at": None,
        "checked_at": now.isoformat(),
        "date_eastern": day.isoformat(),
        "first_tip_at": next_tip.isoformat(),
        "games": [],
        "errors": [],
        "source": "Independently verified dated NBA schedule (not live boxscores)",
        "coverage": {"observed_game_count": 0, "active_or_final_count": 0,
                     "complete": False},
        "not_sportsbook_lines": True,
        "not_ai_projections": True,
    }

def publishable_observations(report):
    """Publish real partial player totals, not an empty or unverified 'live' feed."""
    status=report.get("status")
    return (status=="WAITING_FOR_SCHEDULED_TIPOFF" or
            status in ("OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
                       "PARTIAL_NBA_PLAYER_BOXSCORES") and bool(report.get("games")))

def verified_started(schedule,day,now,grace_minutes=5):
    """A late-running official feed may lag tipoff; do not label it live."""
    if not isinstance(schedule,dict) or schedule.get("coverage_complete") is not True:
        return False
    if day.isoformat() not in (schedule.get("dates_eastern") or []):
        return False
    for g in schedule.get("games",[]):
        if not isinstance(g,dict) or g.get("date_eastern")!=day.isoformat():
            continue
        try:
            kickoff=dt.datetime.fromisoformat(str(g["start"]).replace("Z","+00:00"))
            if kickoff.tzinfo and kickoff<=now-dt.timedelta(minutes=grace_minutes):
                return True
        except (TypeError,ValueError,KeyError):
            continue
    return False

def main():
    day = dt.datetime.now(EASTERN).date()
    schedule = None
    schedule_path = ROOT / "docs/nba_schedule.json"
    if schedule_path.exists():
        try:
            schedule = json.loads(schedule_path.read_text())
        except (ValueError, OSError):
            schedule = None
    report = waiting_for_tipoff(schedule, day)
    if report is None:
     try:
        report = collect_boxscores(day)
     except (OSError, RuntimeError, ValueError, KeyError, TypeError) as err:
        report = {"status":"NBA_PLAYER_BOXSCORES_UNAVAILABLE",
                  "captured_at":None, "last_attempt_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                  "date_eastern":day.isoformat(), "games":[], "errors":[type(err).__name__]}
    if (report.get("status")=="OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES" and
        not report.get("games") and
        verified_started(schedule,day,dt.datetime.now(dt.timezone.utc))):
        report["status"]="PARTIAL_NBA_PLAYER_BOXSCORES"
        report.setdefault("errors",[]).append("SCHEDULE_STARTED_BUT_OFFICIAL_PLAYER_TOTALS_MISSING")
        report["coverage"]["complete"]=False
    OUTPUT.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"status":report["status"],"date":day.isoformat(),
                      "observed_games":len(report["games"]),"errors":report["errors"]}))
    # A real partial slate is worth publishing. The next audit still marks
    # uncovered started games degraded until genuine rows arrive.
    if not publishable_observations(report):
        raise SystemExit(1)

if __name__ == "__main__":
    main()

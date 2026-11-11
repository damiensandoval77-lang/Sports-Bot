#!/usr/bin/env python3
"""Capture NBA liveData player box scores with explicit source and freshness.

This free public-data research feed does not infer betting lines, model
projections or player availability. Empty pregame slates aren't live stats.
"""
import datetime as dt
import json
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

def collect_boxscores(day, fetch=request_json, now=None, max_games=15):
    now = now or dt.datetime.now(dt.timezone.utc)
    if not (1 <= max_games <= 15):
        raise ValueError("max_games must be between 1 and 15")
    failures = []
    scoreboard = None
    for url in NBA_LIVE_URLS:
        try:
            result = fetch(url)
            scoreboard = result["scoreboard"]
            if not isinstance(scoreboard.get("games"), list):
                raise ValueError("Malformed liveData scoreboard")
            break
        except (OSError, ValueError, TypeError, KeyError, TimeoutError) as err:
            failures.append(type(err).__name__)
    if scoreboard is None:
        raise RuntimeError("NBA liveData scoreboard unavailable: " + ",".join(failures))
    if scoreboard.get("gameDate") and scoreboard["gameDate"] != day.isoformat():
        raise ValueError("NBA liveData scoreboard has not rolled to the requested Eastern date")
    games = []
    for raw in scoreboard["games"]:
        parsed = parse_nba_game(raw, {day})
        if not parsed or parsed["game_state"] not in ("in", "post"):
            continue
        if len(games) >= max_games:
            raise ValueError("Active game limit exceeded; cannot claim full coverage")
        gid = str(raw.get("gameId") or "")
        if not gid.isdigit() or len(gid) != 10:
            failures.append("INVALID_GAME_ID")
            continue
        box = None
        for prefix in BOX_BASES:
            try:
                response = fetch(prefix + gid + ".json")
                box = response["game"]
                if str(box.get("gameId")) != gid:
                    raise ValueError("Boxscore/game id mismatch")
                break
            except (OSError, ValueError, TypeError, KeyError, TimeoutError) as err:
                failures.append("BOXSCORE_" + type(err).__name__)
        if box is None:
            continue
        rows = []
        for kind in ("awayTeam", "homeTeam"):
            team = box.get(kind) or {}
            tricode = team.get("teamTricode")
            if tricode != raw.get(kind, {}).get("teamTricode"):
                raise ValueError("Boxscore team mismatch")
            for player in team.get("players") or []:
                stats = player.get("statistics") or {}
                pid = player.get("personId")
                if not pid or not player.get("name"):
                    continue
                vals = (stats.get("points"), stats.get("reboundsTotal"), stats.get("assists"))
                if any(type(n) not in (int, float) or n < 0 for n in vals):
                    continue
                pts, reb, ast = vals
                rows.append({"player": player["name"], "player_id": str(pid), "team": tricode,
                             "PTS": pts, "REB": reb, "AST": ast, "PRA": pts + reb + ast})
        if not rows:
            failures.append("EMPTY_PLAYER_BOXSCORE")
            continue
        games.append({"game": parsed["game"], "id": parsed["id"],
                      "state": parsed["game_state"], "period": parsed.get("period"),
                      "shortDetail": raw.get("gameStatusText"),
                      "clock": raw.get("gameClock"),
                      "observed_at": now.isoformat(), "player_rows": rows})
    count_active = sum(
        1 for raw in scoreboard["games"]
        if (parsed := parse_nba_game(raw, {day}))
        and parsed["game_state"] in ("in", "post"))
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

"""Conflict-safe verified NBA live player boxscore publishing.

Never let a partial later observation erase a verified game from the same
Eastern slate. Merge by exact game identity and per-game observation time,
without copying numbers between games or claiming outdated rows are fresh.
Only observed official boxscores can enter this file. No odds credits.
"""
import argparse
import datetime as dt
import json
from pathlib import Path


LIVE = {"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES", "PARTIAL_NBA_PLAYER_BOXSCORES"}
WAITING = "WAITING_FOR_SCHEDULED_TIPOFF"


def parse(raw, *, allow_legacy_suffix=False):
    text = raw
    if allow_legacy_suffix and text.rstrip().endswith(r"\n"):
        text = text.rstrip()[:-2]
    payload = json.loads(text)
    if not isinstance(payload, dict) or not isinstance(payload.get("games"), list):
        raise ValueError("NBA_PLAYER_BOXSCORE_INVALID_SCHEMA")
    return payload


def time_value(raw):
    if not raw:
        return None
    try:
        value = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return value.astimezone(dt.timezone.utc) if value.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def stamp(obj):
    return time_value(obj.get("captured_at") or obj.get("checked_at"))


def game_key(row):
    """Use the full official ID when present; otherwise the exact matchup."""
    if not isinstance(row, dict):
        raise ValueError("NBA_PLAYER_BOXSCORE_GAME_NOT_OBJECT")
    identity = str(row.get("id") or row.get("game") or "").strip()
    if not identity:
        raise ValueError("NBA_PLAYER_BOXSCORE_GAME_IDENTITY_MISSING")
    return identity


def validate_games(report):
    seen = set()
    for game in report.get("games", []):
        identity = game_key(game)
        if identity in seen:
            raise ValueError("NBA_PLAYER_BOXSCORE_DUPLICATE_GAME")
        seen.add(identity)
        if report.get("status") in LIVE and game.get("player_rows") is not None:
            if not isinstance(game["player_rows"], list):
                raise ValueError("NBA_PLAYER_BOXSCORE_INVALID_PLAYER_ROWS")


def observation(row, report):
    return time_value(row.get("observed_at")) or stamp(report)


def merge(old_raw, new_raw):
    new = parse(new_raw)
    old = parse(old_raw, allow_legacy_suffix=True) if old_raw is not None else None
    current_stamp = stamp(new)
    if current_stamp is None:
        raise ValueError("NBA_PLAYER_BOXSCORE_INCOMING_TIMESTAMP_INVALID")
    validate_games(new)
    if not old:
        return new
    validate_games(old)
    previous_stamp = stamp(old)
    # Never overwrite newer observations with an earlier completed workflow.
    if previous_stamp and previous_stamp > current_stamp:
        return old
    # New Eastern dates are separate slates; don't leak previous day boxes.
    if old.get("date_eastern") != new.get("date_eastern"):
        return new
    if old.get("status") in LIVE and new.get("status") == WAITING:
        return old
    if old.get("games") and not new.get("games"):
        return old
    if new.get("status") not in LIVE:
        return old if old.get("status") in LIVE else new
    if old.get("status") not in LIVE or not old.get("games"):
        return new

    # Retain source-linked old observations for other games if this fetch only
    # observed some games. No synthesis of rows and no player-level mixing.
    combined = {}
    for game in old["games"]:
        combined[game_key(game)] = (dict(game), observation(game, old))
    kept_previous = 0
    for game in new["games"]:
        key = game_key(game)
        existing = combined.get(key)
        if existing:
            prior, at = existing
            if prior.get("game") and game.get("game") and prior["game"] != game["game"]:
                raise ValueError("NBA_PLAYER_BOXSCORE_GAME_IDENTITY_CONFLICT")
            fresh_time = observation(game, new)
            if at and (not fresh_time or fresh_time < at):
                kept_previous += 1
                continue
            if prior.get("player_rows") and not game.get("player_rows"):
                kept_previous += 1
                continue
        combined[key] = (dict(game), observation(game, new))
    for key in {game_key(g) for g in old["games"]}:
        if key not in {game_key(g) for g in new["games"]}:
            kept_previous += 1

    result = dict(new)
    result["games"] = [row for row, _ in combined.values()]
    # Do not claim that a partial provider fetch is complete because old
    # values were retained. Per-game observed_at controls UI freshness.
    expected = max(
        len(result["games"]),
        int((old.get("coverage") or {}).get("active_or_final_count") or 0),
        int((new.get("coverage") or {}).get("active_or_final_count") or 0),
    )
    result["coverage"] = dict(new.get("coverage") or {})
    result["coverage"]["observed_game_count"] = len(result["games"])
    result["coverage"]["active_or_final_count"] = expected
    result["coverage"]["complete"] = (
        new.get("status") == "OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES"
        and (new.get("coverage") or {}).get("complete") is True
        and len(new.get("games") or []) >= expected
    )
    result["status"] = (
        "OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES"
        if result["coverage"]["complete"] else "PARTIAL_NBA_PLAYER_BOXSCORES"
    )
    result["preserved_prior_game_observations"] = kept_previous
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True)
    parser.add_argument("--incoming", required=True)
    args = parser.parse_args()
    path = Path(args.current)
    candidate = Path(args.incoming).read_text(encoding="utf-8")
    old = path.read_text(encoding="utf-8") if path.exists() else None
    result = merge(old, candidate)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("Independent NBA player snapshot published:",
          result.get("status"), len(result["games"]), "games",
          "prior observations retained:", result.get("preserved_prior_game_observations", 0))


if __name__ == "__main__":
    main()

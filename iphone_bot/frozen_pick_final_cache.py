"""Resolve frozen pick outcomes without requiring a separate model's forecast.

Only missing outcome identities are added from official, exact-identity NBA
final cache rows. No forecast is created and no existing final is overwritten.
"""
import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from iphone_bot.paper_pick_pipeline import expected_opponents, strict_player_name
from iphone_bot.verified_final_cache import verified_row

FIELDS = ("player_id", "team", "game", "start", "stat")

def identity(row):
    return tuple(str(row.get(field) or "") for field in FIELDS)

def augment_final_outcomes(frozen, finals, cache_rows):
    records = list(finals.get("records", []))
    existing = {identity(row) for row in records if isinstance(row, dict)}
    for pick in frozen.get("records", []):
        if not isinstance(pick, dict) or not isinstance(pick.get("start"), str):
            continue
        if not all(pick.get(field) for field in FIELDS) or not str(pick["player_id"]).isdigit() or not strict_player_name(pick.get("player")):
            continue
        key = identity(pick)
        if key in existing or pick.get("stat") not in {"PTS", "REB", "AST", "PRA"}:
            continue
        try:
            start = dt.datetime.fromisoformat(pick["start"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                continue
            day = start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        except (KeyError, TypeError, ValueError):
            continue
        opponents = expected_opponents(pick.get("game"), pick.get("team"))
        if len(opponents) != 1 or pick.get("opponent") not in (None, opponents[0]):
            continue
        matches = [row for row in cache_rows if isinstance(row, dict)
                   and row.get("source") == "NBA_CDN_FINAL"
                   and str(row.get("nba_person_id") or "") == str(pick.get("player_id") or "")
                   and strict_player_name(row.get("player")) == strict_player_name(pick.get("player"))
                   and row.get("team") == pick.get("team")
                   and row.get("opponent") == opponents[0] and row.get("date") == day]
        if not matches or any(not verified_row(row) for row in matches):
            continue
        row = matches[0]
        # Fail closed for contradictory totals, DNP status, or event IDs.
        evidence = ("source_game_id", "PTS", "REB", "AST", "PRA", "MIN", "dnp_final_verified", "dnp_reason")
        if any(any(other.get(k) != row.get(k) for k in evidence) for other in matches):
            continue
        if not re.fullmatch(r"00\d{8}", str(row.get("source_game_id") or "")):
            continue
        outcome = {field: pick[field] for field in FIELDS}
        outcome.update(final_source="NBA_CDN_FINAL", source_game_id=row["source_game_id"],
                       outcome_provenance="EXACT_OFFICIAL_FINAL_PLAYER_CACHE")
        if row.get("dnp_final_verified") is True:
            outcome.update(status="EXCLUDED_VERIFIED_DNP", actual=None,
                           verified_dnp_reason=row["dnp_reason"])
        else:
            outcome.update(status="GRADED", actual=row[pick["stat"]])
        records.append(outcome)
        existing.add(key)
    return {**finals, "records": records}

def with_cached_outcomes(frozen, finals, path):
    try:
        cache = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return finals
    if not isinstance(cache, dict) or cache.get("version") != 1 or not isinstance(cache.get("rows"), list):
        return finals
    return augment_final_outcomes(frozen, finals, cache["rows"])

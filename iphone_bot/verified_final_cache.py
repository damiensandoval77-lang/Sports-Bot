"""Persistent, independently verified final NBA player rows for outage recovery.

Only validated rows originally retrieved from NBA CDN or ESPN final boxes can be
cached. Never interpret an absent player as zero or an unverified DNP.
"""
import json
import math
from pathlib import Path
from iphone_bot.fetch_final_boxscores import ABBREV

SOURCES = {"NBA_CDN_FINAL", "ESPN_FINAL"}
STATS = ("PTS", "REB", "AST", "PRA", "MIN")

def verified_row(row):
    if not isinstance(row, dict) or row.get("final_confirmed") is not True:
        return False
    if row.get("source") not in SOURCES or not str(row.get("source_game_id") or "").strip():
        return False
    if not isinstance(row.get("player"), str) or not row["player"].strip():
        return False
    if row.get("team") not in ABBREV or row.get("opponent") not in ABBREV or row["team"] == row["opponent"]:
        return False
    day = row.get("date")
    if not isinstance(day, str) or len(day) != 10:
        return False
    try:
        import datetime
        if datetime.date.fromisoformat(day).isoformat() != day:
            return False
    except ValueError:
        return False
    if row.get("dnp_final_verified") is True:
        return isinstance(row.get("dnp_reason"), str) and bool(row["dnp_reason"].strip())
    try:
        values = [float(row[k]) for k in STATS]
    except (TypeError, ValueError, KeyError):
        return False
    return (all(math.isfinite(x) for x in values)
            and all(0 <= x <= 250 for x in values[:4])
            and 0 < values[4] <= 60
            and abs(values[3] - sum(values[:3])) < 0.01)

def row_key(row):
    return tuple(str(row.get(field, "")) for field in
                 ("source_game_id", "date", "team", "opponent", "player"))

def merge_rows(prior, new):
    """Keep only trusted sources and reject conflicting identities."""
    chosen = {}
    conflicts = set()
    for row in list(prior) + list(new):
        if not verified_row(row):
            continue
        ident = row_key(row)
        if ident in chosen and chosen[ident] != row:
            conflicts.add(ident)
        else:
            chosen.setdefault(ident, row)
    return [chosen[k] for k in sorted(chosen) if k not in conflicts]

def read_cache(path):
    try:
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict) or data.get("version") != 1:
            return []
        return merge_rows([], data.get("rows", []))
    except (OSError, TypeError, ValueError):
        return []

def write_cache(path, prior, fetched):
    rows = merge_rows(prior, fetched)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps({"version": 1, "rows": rows}, indent=2) + "\n")
    return rows

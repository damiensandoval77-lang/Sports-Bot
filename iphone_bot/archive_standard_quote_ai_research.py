"""Durable, strictly pretip standard-line × AI research receipts.

Independent from the validated model simulation ledger and official grading.
Never promotes stale, post-tip, alternative-tier or research-only estimates into
validated picks. Historical records survive provider outages and price moves.
"""
import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCOMING = ROOT / "docs/ai_prizepicks_quick_join.json"
OUT = ROOT / "docs/standard_quote_ai_research_archive.json"
STATUS = "IMMUTABLE_PRETIP_STANDARD_QUOTE_AI_RESEARCH"
SOURCE_STATUS = "FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS"

def moment(value):
    try:
        t = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if t.tzinfo is None or t.utcoffset() is None:
            return None
        return t.astimezone(dt.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None

def identity(record):
    # One immutable research observation per exact player/event/stat/standard
    # threshold. Repeated refreshes do not inflate historical hit-rate samples.
    return tuple(str(record.get(k, "")) for k in (
        "source", "player_id", "team", "game", "start", "stat", "line"
    ))

def valid(row, now):
    if not isinstance(row, dict):
        return False
    if (row.get("research_only") is not True or row.get("source") != "independent_prizepicksapi_com"
            or row.get("more_tier") != "standard" or row.get("less_tier") != "standard"
            or row.get("stat") not in {"PTS", "REB", "AST", "PRA"}
            or row.get("confidence_percent") is not None
            or row.get("estimated_ev") is not None
            or row.get("reliability_screen", {}).get("validated") is not False):
        return False
    if not all(row.get(k) for k in ("provider_projection_id", "player", "player_id", "team", "game", "stat")):
        return False
    start = moment(row.get("start"))
    observed = moment(row.get("observed_at"))
    model_time = moment(row.get("model_generated_at"))
    if not start or not observed or not model_time or not (observed <= now and model_time <= now and observed < start and model_time < start and now < start):
        return False
    try:
        line = float(row["line"])
        projection = float(row["projection"])
    except (ValueError, TypeError, KeyError):
        return False
    return all(math.isfinite(x) for x in (line, projection)) and 0 <= line <= 200 and 0 <= projection <= 250

def merge(incoming, previous=None, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    old = previous or {}
    if old and old.get("status") != STATUS:
        raise ValueError("Previous archive type invalid; refusing to overwrite")
    records = {}
    for row in old.get("records", []):
        key = identity(row)
        if key in records and row != records[key]:
            raise ValueError("Contradictory previously frozen research quote")
        records[key] = row
    added = 0
    captured = moment(incoming.get("generated_at"))
    fresh_snapshot = captured is None or (dt.timedelta(0) <= now - captured <= dt.timedelta(minutes=90))
    if incoming.get("status") == SOURCE_STATUS and fresh_snapshot:
        for row in incoming.get("comparisons", []):
            if not valid(row, now):
                continue
            key = identity(row)
            if key in records:
                # The originally frozen projection wins. Never rewrite it when
                # a repeated provider observation or refreshed model differs.
                continue
            source_snapshot = {k: row.get(k) for k in (
                "source", "provider_projection_id", "player", "player_id", "team",
                "opponent", "game", "start", "stat", "line", "observed_at",
                "model_generated_at", "projection", "ai_direction", "more_tier", "less_tier"
            )}
            records[key] = {
                **source_snapshot, "source_snapshot": source_snapshot,
                "research_only": True, "calibrated": False,
                "grade": "UNSETTLED_RESEARCH", "actual": None,
                "direction_hit": None, "grade_source": None,
                "frozen_at": now.isoformat()
            }
            added += 1
    # Replaying an unchanged provider/model snapshot must not produce another
    # git commit or GitHub Pages rebuild; retain the old archive byte-for-byte.
    if added == 0 and old.get("status") == STATUS:
        return old
    result = sorted(records.values(), key=lambda x: (
        x.get("start", ""), x.get("game", ""), x.get("player_id", ""), x.get("stat", ""), str(x.get("line", ""))
    ))
    return {
        "status": STATUS, "updated_at": now.isoformat(),
        "records": result, "count": len(result), "new_records": added,
        "source_status": incoming.get("status"),
        "note": "Research-only historical capture. No simulated hit probability or official grade; never substitute for validated frozen-model ledger."
    }

def main():
    def read(path):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return {}
    result = merge(read(INCOMING), read(OUT))
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print("Immutable research quote receipts:", result["count"], "added:", result["new_records"])

if __name__ == "__main__":
    main()

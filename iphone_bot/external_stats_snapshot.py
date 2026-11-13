"""Validated external NBA statistical snapshots for OFFLINE research only.

This module does not scrape, download, or access NBAstuffer. Use only datasets
you are authorized to import. Never use the snapshots as sportsbook quotes or
replace production forecasts. Season aggregates are not game logs or DvP.
"""
import csv
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

PLAYER_REQUIRED = {"NAME", "TEAM", "GP", "MpG", "USG%", "PpG", "RpG", "ApG"}
TEAM_REQUIRED = {"TEAM", "GP", "PACE", "oEFF", "dEFF"}
PLAYER_NUMERIC = {"GP", "MpG", "USG%", "PpG", "RpG", "ApG", "TS%", "3P%", "3PA", "2PA", "ORtg", "DRtg"}
TEAM_NUMERIC = {"GP", "PACE", "oEFF", "dEFF", "PPG", "oPPG"}
ALLOWED_SEASONS = {"2026-2027"}
MAX_AGE_DAYS = 3


class SnapshotError(ValueError):
    """Invalid, stale or unlicensed statistical snapshot."""


def _date(value):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError) as exc:
        raise SnapshotError("Invalid as_of date") from exc


def load_snapshot(csv_path, manifest_path, kind, *, today=None):
    """Return validated rows and provenance, without any network requests.

    The caller explicitly supplies a CSV and manifest. Manifest keys:
      source_name, source_url, season, as_of, rights_confirmed, research_only.
    No source gets automatic permission through being publicly readable.
    """
    if kind not in ("player", "team"):
        raise SnapshotError("kind must be player or team")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not manifest.get("rights_confirmed", False):
        raise SnapshotError("Source usage rights have not been confirmed")
    if manifest.get("research_only") is not True:
        raise SnapshotError("Snapshot must be designated research_only")
    if manifest.get("season") not in ALLOWED_SEASONS:
        raise SnapshotError("Unexpected season")
    if not manifest.get("source_name") or not manifest.get("source_url"):
        raise SnapshotError("Missing source provenance")
    as_of = _date(manifest.get("as_of"))
    today = today or datetime.now(timezone.utc).date()
    if as_of > today or (today - as_of).days > MAX_AGE_DAYS:
        raise SnapshotError("Snapshot is future-dated or stale")
    required = PLAYER_REQUIRED if kind == "player" else TEAM_REQUIRED
    numeric = PLAYER_NUMERIC if kind == "player" else TEAM_NUMERIC
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        if not required <= headers:
            raise SnapshotError("Missing mandatory columns: " + ", ".join(sorted(required - headers)))
        rows = []
        identities = set()
        for item in reader:
            if not any(str(v or "").strip() for v in item.values()):
                continue
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in item.items()}
            key = (row.get("NAME"), row.get("TEAM")) if kind == "player" else (row.get("TEAM"),)
            if any(not v for v in key) or key in identities:
                raise SnapshotError("Missing or duplicate entity identity")
            identities.add(key)
            for field in numeric & headers:
                value = row.get(field)
                if value in ("", None):
                    row[field] = None
                    continue
                try:
                    number = float(value)
                except (TypeError, ValueError) as exc:
                    raise SnapshotError("Non-numeric value in " + field) from exc
                if not math.isfinite(number) or number < 0:
                    raise SnapshotError("Invalid value in " + field)
                row[field] = number
            if row["GP"] is None or not 1 <= row["GP"] <= 90:
                raise SnapshotError("Invalid games played")
            if kind == "player" and (row["MpG"] is None or row["MpG"] > 48):
                raise SnapshotError("Invalid minutes per game")
            if kind == "team" and (row["PACE"] is None or not 60 <= row["PACE"] <= 140):
                raise SnapshotError("Invalid team pace")
            rows.append(row)
    if not rows:
        raise SnapshotError("Empty snapshot")
    return {"status": "VALIDATED_OFFLINE_RESEARCH_ONLY", "kind": kind,
            "season": manifest["season"], "as_of": as_of.isoformat(),
            "source_name": manifest["source_name"], "source_url": manifest["source_url"],
            "rows": rows, "production_modified": False,
            "position_defense_verified": False, "calibrated": False}

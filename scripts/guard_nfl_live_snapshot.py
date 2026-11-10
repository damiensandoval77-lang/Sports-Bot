"""Prevent out-of-order or degraded NFL live snapshots replacing verified data.

Used after fetching the latest main branch in the publishing retry loop. Only
writes the isolated live snapshot. No frozen lines, picks, or grades are edited.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def timestamp(value):
    try:
        dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if dt.tzinfo is None:return None
        return dt.astimezone(timezone.utc)
    except (TypeError,ValueError):
        return None


def valid(record):
    if not isinstance(record,dict) or record.get("season")!=2026:return False
    if not isinstance(record.get("games"),list):return False
    if timestamp(record.get("checked_at")) is None:return False
    if record.get("status") not in ("ok","partial_or_unavailable","no_active_window"):return False
    for game in record["games"]:
        if not isinstance(game,dict) or not game.get("game_id") or not isinstance(game.get("players"),list):
            return False
        if game.get("status") not in ("pre","in","post","unknown"):return False
    return True


def should_publish(existing,new):
    if not valid(new):return False,"invalid_new_snapshot"
    if not new["games"]:
        return False,"empty_or_no_active_game_snapshot"
    if new.get("status")!="ok":
        return False,"partial_provider_response"
    if not valid(existing):return True,"new_valid_snapshot"
    old_at=timestamp(existing["checked_at"])
    new_at=timestamp(new["checked_at"])
    if new_at<=old_at:return False,"older_or_duplicate_snapshot"
    old_games={x["game_id"]:x for x in existing["games"]}
    for game in new["games"]:
        previous=old_games.get(game["game_id"])
        if not previous:continue
        if previous["status"] in ("in","post") and game["status"] in ("pre","unknown"):
            return False,"status_regressed"
        if previous["status"]=="post" and game["status"]!="post":
            return False,"final_status_regressed"
        if len(game["players"])<len(previous["players"]) and previous["status"] in ("in","post"):
            return False,"player_coverage_regressed"
    return True,"verified_newer_snapshot"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--previous",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    a=p.parse_args()
    try:
        existing=json.loads(a.previous.read_text()) if a.previous.exists() else None
        incoming=json.loads(a.candidate.read_text())
    except (OSError,ValueError) as e:
        raise SystemExit("Unsafe NFL snapshot input: "+type(e).__name__)
    publish,reason=should_publish(existing,incoming)
    print("NFL LIVE MONOTONIC GUARD:",reason,"publish" if publish else "skip",flush=True)
    if not publish:raise SystemExit(10)


if __name__=="__main__":main()

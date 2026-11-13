"""Recover historical ESPN event IDs only from immutable saved NBA schedules.

An archived scheduled matchup is a lookup hint, never a final boxscore.
Conflicting archived IDs are rejected; ESPN's completed final summary must
still attest the event ID, teams, local game date and final status.
"""
import gzip
import json
from pathlib import Path
from iphone_bot.fetch_final_boxscores import verified_espn_schedule_hints

ROOT=Path(__file__).resolve().parents[1]
ARCHIVES=ROOT/"docs/research_inputs/schedule"
MAX_FILES=240

def archived_espn_hints(root=ARCHIVES,dates=None):
    root=Path(root)
    files=sorted(root.glob("*/*.json.gz"))
    if len(files)>MAX_FILES:
        # Read newest bounded archive files; never scan arbitrary file paths.
        files=files[-MAX_FILES:]
    candidates={}
    conflicting=set()
    for path in files:
        if dates is not None and path.parent.name not in dates:
            continue
        try:
            if path.stat().st_size>4_000_000:continue
            with gzip.open(path,"rt",encoding="utf-8") as handle:
                snapshot=json.load(handle)
            if snapshot.get("status")!="ORIGINAL_REPORTED_NBA_FIXTURES_ARCHIVE":
                continue
            slate=snapshot.get("schedule")
            if not isinstance(slate,dict):continue
            # The base parser performs exact ESPN ID, Eastern date, team,
            # event-start, and schedule status validation.
            for key,event_id in verified_espn_schedule_hints(slate).items():
                # NBA official game IDs are not ESPN summary endpoints.
                if len(event_id)<9 or event_id.startswith("00226"):continue
                if dates is not None and key[0] not in dates:continue
                if key in candidates and candidates[key]!=event_id:
                    conflicting.add(key)
                else:candidates.setdefault(key,event_id)
        except (OSError,EOFError,ValueError,TypeError,UnicodeDecodeError):
            continue
    return {key:event_id for key,event_id in candidates.items()
            if key not in conflicting}

def combine_espn_hints(current,archived):
    """A same-day conflict rejects both rather than picking a convenient ID."""
    result=dict(archived)
    for key,event_id in current.items():
        if key in result and result[key]!=event_id:
            result.pop(key)
        else:result[key]=event_id
    return result

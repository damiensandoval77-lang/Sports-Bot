"""Resolve only explicitly sourced no-play NBA outcomes; never score DNP as win/loss.

The fixture is manually curated from public NBA postgame reports, not an
automatic inference from a missing player row. All identities must match the
saved pregame capture exactly, including team, matchup and Eastern date.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from .paper_pick_pipeline import utc,strict_player_name
except ImportError:
    from paper_pick_pipeline import utc,strict_player_name

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"docs/verified_dnp_outcomes.json"
ET=ZoneInfo("America/New_York")

def apply_verified_dnp(rows,fixture,now=None):
    if fixture.get("status")!="MANUALLY_VERIFIED_DNP_FROM_PUBLISHED_TEAM_OR_NBA_REPORTS":
        raise ValueError("DNP fixture lacks explicit verification status")
    entries=fixture.get("records")
    if not isinstance(entries,list):raise ValueError("Invalid DNP records")
    approved={}
    for e in entries:
        source=e.get("source_url","")
        if not isinstance(source,str) or not source.startswith("https://www.nba.com/"):
            raise ValueError("DNP record requires original NBA published source")
        if not e.get("reason") or not e.get("player") or not e.get("game"):
            raise ValueError("DNP record missing identity or rationale")
        key=(str(e["date_eastern"]),str(e["game"]),str(e["team"]),
             str(e["player_id"]))
        if key in approved:raise ValueError("Duplicate DNP player-game identity")
        approved[key]=e
    now=utc(now or datetime.now(timezone.utc).isoformat())
    updated=[]
    for row in rows:
        r=dict(row)
        if r.get("status")!="PENDING":
            updated.append(r)
            continue
        try:
            tip=utc(r["event_start"])
            day=tip.astimezone(ET).date().isoformat()
            key=(day,str(r["game"]),str(r["team"]),str(r["player_id"]))
            e=approved.get(key)
            if (e and now>=tip and utc(r["captured_at"])<tip
                    and strict_player_name(r["player"])==strict_player_name(e["player"])):
                r.update({"status":"VOID_DNP","result":"VOID",
                          "void_reason":e["reason"],
                          "void_source_url":e["source_url"],
                          "void_recorded_at":now.isoformat()})
        except (ValueError,TypeError,KeyError):
            pass
        updated.append(r)
    return updated

def load_fixture(path=FIXTURE):
    return json.loads(Path(path).read_text()) if Path(path).exists() else {"status":"MANUALLY_VERIFIED_DNP_FROM_PUBLISHED_TEAM_OR_NBA_REPORTS","records":[]}

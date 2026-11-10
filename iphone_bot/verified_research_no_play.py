"""Proof-linked, exact-ID no-play recovery for completed historical research.

This cannot award a win/loss or create a numerical stat. A frozen pretip game
must exactly match one of three source-confirmed FINAL NBA boxscore inactives.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"docs/verified_research_dnps_2026-11-06_07.json"
ET=ZoneInfo("America/New_York")
APPROVED={
 ("2026-11-06","0022600027","1628386","Jarrett Allen","CLE","PHI",95,119),
 ("2026-11-07","0022600193","1630217","Desmond Bane","ORL","GSW",119,126),
 ("2026-11-07","0022600192","203076","Anthony Davis","WAS","OKC",75,114)
}

def evidence_map(path=EVIDENCE):
    d=json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("status")!="EXPLICIT_OFFICIAL_FINAL_BOX_INACTIVE" or d.get("season")!="2026-27":
        raise ValueError("Unverified NBA research DNP fixture")
    found={}
    for x in d.get("records",[]):
        ident=(x["date_eastern"],x["game_id"],x["player_id"],x["player"],
               x["team"],x["opponent"],x["away_score"],x["home_score"])
        if ident not in APPROVED:
            raise ValueError("Unexpected research final DNP identity")
        if (x["source_url"]!="https://www.nba.com/game/0022600027/box-score"
           and x["source_url"]!="https://www.nba.com/game/orl-vs-gsw-0022600193/box-score"
           and x["source_url"]!="https://www.nba.com/game/was-vs-okc-0022600192/box-score"):
            raise ValueError("Research DNP must have official NBA final source")
        key=(x["date_eastern"],str(x["player_id"]),x["team"],x["game"])
        if key in found:raise ValueError("Duplicate source-linked research DNP")
        found[key]=x
    if len(found)!=3:raise ValueError("Incomplete official research DNP fixture")
    return found

def match(record,evidence=None,now=None):
    if record.get("status")!="PENDING":return None
    start=record.get("event_start");captured=record.get("captured_at")
    try:
        a=datetime.fromisoformat(str(start).replace("Z","+00:00"))
        b=datetime.fromisoformat(str(captured).replace("Z","+00:00"))
        now=now or datetime.now(timezone.utc)
        if a.tzinfo is None or b.tzinfo is None or not (b<a<now):
            return None
        day=a.astimezone(ET).date().isoformat()
    except (TypeError,ValueError):return None
    by_key=evidence if evidence is not None else evidence_map()
    return by_key.get((day,str(record.get("player_id")),str(record.get("team")),
                       str(record.get("game"))))

def exclude_pending(rows,now=None,evidence=None,minutes_only=False):
    proof=evidence if evidence is not None else evidence_map()
    out=[]
    for original in rows:
        row=dict(original)
        linked=match(row,proof,now)
        if linked:
            row.update(status="EXCLUDED_VERIFIED_DNP" if minutes_only else "VOID_DNP",
                verified_no_play_source=linked["source_url"],
                verified_no_play_game_id=linked["game_id"],
                verified_no_play_reason=linked["reason"])
            if not minutes_only:
                row.update(result="VOID",paper_profit_units=None,actual=None)
        out.append(row)
    return out

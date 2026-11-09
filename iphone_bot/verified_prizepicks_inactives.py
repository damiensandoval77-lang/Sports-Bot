"""Verified one-date official NBA inactive backfill, void-only.

Used ONLY when the NBA final game itself was independently verified and
both public postgame references were manually checked. No stats, odds, or
win/loss results are inferred from an absence.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from iphone_bot.paper_pick_pipeline import strict_player_name

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"docs/verified_prizepicks_inactive_2026-11-08.json"
SOURCE="NBA_OFFICIAL_INACTIVE_CROSSCHECKED"

def verified_inactive_rows(official_rows,fixture,require_all=True):
    if fixture.get("status")!="MANUALLY_CROSSCHECKED_OFFICIAL_NBA_INACTIVE_2026_11_08":
        raise ValueError("Official inactivity evidence not verified")
    day=fixture.get("game_date_eastern")
    if day!="2026-11-08":raise ValueError("Backfill locked to exact evidence date")
    refs={(str(r.get("source_game_id")),r.get("date"),
           r.get("team"),r.get("opponent"))
          for r in official_rows
          if r.get("final_confirmed") is True
          and r.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL")}
    played={(str(r.get("source_game_id")),r.get("date"),
             r.get("team"),strict_player_name(r.get("player")))
            for r in official_rows
            if r.get("final_confirmed") is True
            and not r.get("dnp_final_verified")}
    entries=fixture.get("players")
    if not isinstance(entries,list) or (len(entries)!=4 if require_all else not 1<=len(entries)<=4):
        raise ValueError("Cross-checked November 8 inactive set has invalid entries")
    seen=set()
    result=[]
    for item in entries:
        name=item.get("player")
        team=item.get("team")
        opponent=item.get("opponent")
        gid=str(item.get("game_id"))
        official=item.get("official_inactive_url")
        game=item.get("game_url")
        secondary=item.get("corroboration_url")
        if (not name or not strict_player_name(name) or
            not re.fullmatch(r"00226\d{5}",gid) or
            not team or not opponent or team==opponent or
            (gid,day,team,opponent) not in refs):
            raise ValueError("Unverified completed game or inactive player identity")
        if (not all(isinstance(u,str) and u.startswith("https://") for u in (official,game,secondary)) or
            not all(urlparse(u).hostname in ("nba.com","www.nba.com") for u in (official,game)) or
            gid not in game or
            urlparse(secondary).hostname not in
                ("nba.com","www.nba.com","www.cbssports.com","www.nbcsports.com")):
            raise ValueError("Missing genuine official and corroborated sources")
        identity=(gid,day,team,strict_player_name(name))
        if identity in seen or identity in played:
            raise ValueError("Duplicate or actually played player cannot be manually voided")
        seen.add(identity)
        result.append({
            "player":name,"team":team,"opponent":opponent,"date":day,
            "source_game_id":gid,"final_confirmed":True,
            "dnp_final_verified":True,"dnp_reason":item.get("reason") or "VERIFIED_INACTIVE",
            "source":SOURCE,"official_inactive_url":official,
            "corroboration_url":secondary,"verified_game_url":game,
            "PTS":None,"REB":None,"AST":None,"PRA":None,"MIN":None,
        })
    return result

def load_verified_inactive_rows(official_rows):
    if not FIXTURE.exists():return []
    return verified_inactive_rows(official_rows,json.loads(FIXTURE.read_text()))

def verified_inactive_subset(official_rows):
    """Cross-check only fixture games actually corroborated by this official final batch.

    Never assert a player DNP in a game whose final boxscore was not independently
    retrieved. All selected entries pass the same strict source and identity rules.
    """
    if not FIXTURE.exists():
        return []
    fixture=json.loads(FIXTURE.read_text())
    final_keys={(str(r.get("source_game_id")),r.get("date"),
                 r.get("team"),r.get("opponent"))
                for r in official_rows
                if r.get("final_confirmed") is True
                and r.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL")}
    selected=[r for r in fixture.get("players",[])
              if (str(r.get("game_id")),fixture.get("game_date_eastern"),
                  r.get("team"),r.get("opponent")) in final_keys]
    if not selected:
        return []
    return verified_inactive_rows(official_rows,{**fixture,"players":selected},require_all=False)

AI_INACTIVE_FIXTURE=ROOT/"docs/verified_ai_inactives_2026-11-08.json"

def additional_verified_ai_inactive_subset(official_rows):
    """Source-linked, *AI-only* exclusion for other Nov 8 confirmed absences.

    The original PrizePicks evidence fixture is independent. Only rows whose
    final NBA matchup has been observed from a trusted final source qualify.
    """
    if not AI_INACTIVE_FIXTURE.exists():
        return []
    fixture=json.loads(AI_INACTIVE_FIXTURE.read_text())
    final_keys={(str(r.get("source_game_id")),r.get("date"),
                 r.get("team"),r.get("opponent"))
                for r in official_rows if r.get("final_confirmed") is True
                and r.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL")}
    selected=[r for r in fixture.get("players",[])
              if (str(r.get("game_id")),fixture.get("game_date_eastern"),
                  r.get("team"),r.get("opponent")) in final_keys]
    if not selected:
        return []
    return verified_inactive_rows(official_rows,{**fixture,"players":selected},
                                  require_all=False)

"""Source-linked Nov 8 final-boxscore DNP recovery for AI forecast accuracy only.

Manual source evidence is limited to listed explicit DNPs. A verified NBA/ESPN
final-game row must independently establish the final matchup before use.
"""
import json
from pathlib import Path
from urllib.parse import urlparse
from iphone_bot.paper_pick_pipeline import strict_player_name

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"docs/verified_boxscore_dnps_2026-11-08.json"
SOURCE="VERIFIED_FINAL_BOXSCORE_DNP_CROSSCHECKED"
ALLOWED={"www.covers.com","americanbball.com","fantasyteamadvice.com"}
EXPECTED={
    ("Dru Smith","MIA","SAC"),("Myron Gardner","MIA","SAC"),
    ("Nick Richards","MIA","SAC"),("Nikola Jović","MIA","SAC"),
    ("Alex Karaban","SAC","MIA"),
}

def verified_boxscore_dnp_rows(final_rows,fixture):
    if fixture.get("status")!="SOURCE_CROSSCHECKED_EXPLICIT_FINAL_BOXSCORE_DNP" or fixture.get("date_eastern")!="2026-11-08" or str(fixture.get("game_id"))!="0022600202":
        raise ValueError("Invalid exact historical source fixture")
    items=fixture.get("players")
    if not isinstance(items,list) or len(items)!=5 or {(x.get("player"),x.get("team"),x.get("opponent")) for x in items if isinstance(x,dict)}!=EXPECTED:
        raise ValueError("Source fixture changed or has unknown players")
    if fixture.get("official_final_game_url")!="https://www.nba.com/game/0022600202":
        raise ValueError("Official final game identity mismatch")
    verified={(str(r.get("source_game_id")),r.get("date"),r.get("team"),r.get("opponent"))
              for r in final_rows
              if r.get("final_confirmed") is True and r.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL")}
    played={(str(r.get("source_game_id")),r.get("date"),r.get("team"),strict_player_name(r.get("player")))
            for r in final_rows if r.get("final_confirmed") is True and not r.get("dnp_final_verified")}
    result=[]
    for x in items:
        name,team,opp=x["player"],x["team"],x["opponent"]
        k=("0022600202","2026-11-08",team,opp)
        if k not in verified:continue
        if ("0022600202","2026-11-08",team,strict_player_name(name)) in played:
            raise ValueError("Conflicting played row: "+name)
        a,b=x.get("primary_url"),x.get("corroboration_url")
        if not all(isinstance(u,str) and u.startswith("https://") for u in (a,b)) or urlparse(a).hostname not in ALLOWED or urlparse(b).hostname not in ALLOWED or a==b or not str(x.get("reason","")).startswith("DNP"):
            raise ValueError("Missing explicit DNP source documentation")
        result.append({"player":name,"team":team,"opponent":opp,"date":"2026-11-08",
            "source_game_id":"0022600202","final_confirmed":True,
            "dnp_final_verified":True,"dnp_reason":x["reason"],"source":SOURCE,
            "primary_url":a,"corroboration_url":b,
            "PTS":None,"REB":None,"AST":None,"PRA":None,"MIN":None})
    return result

def verified_boxscore_dnp_subset(final_rows,path=FIXTURE):
    if not path.exists():return []
    return verified_boxscore_dnp_rows(final_rows,json.loads(path.read_text()))

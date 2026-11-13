"""Official NBA Nov 9 explicit DNP evidence, crosschecked against verified FINAL player rows.

The fixture is not evidence a game finished. Matching previously verified FINAL
player rows independently establish that game's ID, date, and both teams.
No existing played row may be excluded. Missing players outside this fixture
remain pending.
"""
import json
from pathlib import Path
from iphone_bot.paper_pick_pipeline import strict_player_name
from iphone_bot.fetch_final_boxscores import verified_dnp_player

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"docs/verified_nba_dnp_2026-11-09.json"
SOURCE="NBA_OFFICIAL_FINAL_BOXSCORE_DNP_CROSSCHECKED"
VALID_SOURCES={"NBA_CDN_FINAL","ESPN_FINAL"}
ALLOWED_GAME_IDS={"0022600203","0022600207","0022600208"}

def crosschecked_official_dnp(final_rows,fixture):
    if fixture.get("status")!="OFFICIAL_NBA_FINAL_EXPLICIT_DNP_CROSSCHECK" or fixture.get("date_eastern")!="2026-11-09":
        raise ValueError("Invalid official NBA DNP fixture")
    output=[]
    for game in fixture.get("games",[]):
        gid=str(game.get("game_id") or "")
        away,home=game.get("away"),game.get("home")
        url=game.get("source_url","")
        if gid not in ALLOWED_GAME_IDS or not url.startswith("https://www.nba.com/") or not gid in url:
            raise ValueError("Missing official NBA source")
        # Independently verified played rows for BOTH teams establish the final
        # matchup. Never validate only a cached score, schedule or page URL.
        verified=[r for r in final_rows if
            str(r.get("source_game_id"))==gid and
            r.get("date")=="2026-11-09" and
            r.get("final_confirmed") is True and
            r.get("source") in VALID_SOURCES and
            not r.get("dnp_final_verified") and
            (r.get("team"),r.get("opponent")) in ((away,home),(home,away))]
        if len([r for r in verified if r["team"]==away])<3 or len([r for r in verified if r["team"]==home])<3:
            continue
        for item in game.get("players",[]):
            name=item.get("player")
            team=item.get("team")
            if team not in (away,home) or item.get("reason")!="DNP - Coach's Decision" or not strict_player_name(name):
                raise ValueError("Invalid sourced NBA DNP identity")
            opp=home if team==away else away
            if any(r["team"]==team and strict_player_name(r.get("player"))==strict_player_name(name) for r in verified):
                # Contradictory verified participation is never a DNP.
                continue
            row=verified_dnp_player(name,team,opp,"2026-11-09",item["reason"],"NBA_CDN_FINAL",gid)
            if row:
                row["official_dnp_source_url"]=url
                row["official_dnp_crosscheck"]=SOURCE
                output.append(row)
    pairs=[(x["source_game_id"],x["team"],strict_player_name(x["player"])) for x in output]
    if len(set(pairs))!=len(pairs):raise ValueError("Duplicate official DNP identity")
    return output

def load_official_dnp(final_rows,path=FIXTURE):
    try:return crosschecked_official_dnp(final_rows,json.loads(Path(path).read_text()))
    except OSError:return []

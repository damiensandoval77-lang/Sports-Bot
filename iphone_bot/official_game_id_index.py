"""Durable game-ID discovery ONLY from observed NBA official liveData scoreboards.

Keeps an exact Eastern-day, away/home, NBA game ID index across the daily
scoreboard rollover. IDs locate later boxscores; they never establish a final
score or player stats. Final status and identity must still be checked from
the game box itself.
"""
import datetime as dt
import json
import re
from pathlib import Path
from iphone_bot.fetch_final_boxscores import ABBREV, local_date, team

VALID_ID=re.compile(r"00226\d{5}\Z")

def verified_index_entry(game):
    if not isinstance(game,dict):return None
    game_id=str(game.get("id") or "")
    day=game.get("date_eastern")
    away=team(game.get("away_abbreviation"))
    home=team(game.get("home_abbreviation"))
    start=game.get("start")
    if not VALID_ID.fullmatch(game_id) or not day or away not in ABBREV or home not in ABBREV or away==home:
        return None
    try:
        if dt.date.fromisoformat(day).isoformat()!=day:
            return None
        if local_date(start)!=day:
            return None
    except (ValueError,TypeError):
        return None
    return {"date":day,"away":away,"home":home,"game_id":game_id}

def entries_from_scoreboard(scoreboard):
    if not isinstance(scoreboard,dict) or scoreboard.get("status")!="OBSERVED_NBA_LIVE_SCOREBOARD" or (
        "NBA official liveData scoreboard" not in str(scoreboard.get("source") or "")
    ):
        return []
    return [entry for g in scoreboard.get("games",[]) if (entry:=verified_index_entry(g))]

def merge_entries(existing,new):
    """Conflicting IDs for one matchup are dropped instead of guessed."""
    chosen={}
    conflicts=set()
    for row in list(existing)+list(new):
        if not isinstance(row,dict):continue
        # Index entry identity is revalidated without depending on an invented
        # start time; a game date and exact official NBA identity are sufficient.
        day,away,home,gid=row.get("date"),row.get("away"),row.get("home"),str(row.get("game_id") or "")
        try: dt.date.fromisoformat(day)
        except (ValueError,TypeError):continue
        if not VALID_ID.fullmatch(gid) or away not in ABBREV or home not in ABBREV or away==home:continue
        key=(day,away,home)
        if key in chosen and chosen[key]!=gid:conflicts.add(key)
        else:chosen.setdefault(key,gid)
    return [{"date":d,"away":a,"home":h,"game_id":chosen[(d,a,h)]}
            for d,a,h in sorted(chosen) if (d,a,h) not in conflicts]

def read_index(path):
    try:
        obj=json.loads(Path(path).read_text())
        if obj.get("version")!=1 or not isinstance(obj.get("games"),list):return []
        return merge_entries([],obj["games"])
    except (OSError,TypeError,ValueError,AttributeError):
        return []

def update_index(path,scoreboard):
    path=Path(path)
    old=read_index(path)
    new=merge_entries(old,entries_from_scoreboard(scoreboard))
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({"version":1,"games":new},indent=2)+"\n")
    return len(new)

def matching_ids(entries,pending):
    matches={}
    for row in merge_entries([],entries):
        key=(row["date"],row["away"],row["home"])
        if key in pending:matches[key]=row["game_id"]
    return matches

def read_official_page_hints(path):
    """Sourced NBA.com game page IDs are only hints; final box verifies again."""
    try:
        obj=json.loads(Path(path).read_text())
        if obj.get("version")!=1 or not isinstance(obj.get("games"),list):
            return []
        permitted=[]
        for entry in obj["games"]:
            if not isinstance(entry,dict) or entry.get("source")!="NBA_OFFICIAL_GAME_PAGE":
                continue
            gid=str(entry.get("game_id") or "")
            if not VALID_ID.fullmatch(gid):continue
            if entry.get("url")!=f"https://www.nba.com/game/{gid}":continue
            try:
                day=entry["date"]
                if dt.date.fromisoformat(day).isoformat()!=day:continue
            except (TypeError,ValueError,KeyError):continue
            permitted.append({k:entry[k] for k in ("date","away","home","game_id")})
        return merge_entries([],permitted)
    except (OSError,TypeError,ValueError,AttributeError):
        return []

def recovery_game_ids(index_path,official_page_path):
    """Fail closed on conflicting official ID hints for the same matchup."""
    return merge_entries(read_index(index_path),read_official_page_hints(official_page_path))

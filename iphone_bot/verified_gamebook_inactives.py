"""Load reviewed official final gamebook inactivity evidence for an exact fixture."""
import json
import re
from pathlib import Path

from iphone_bot.fetch_final_boxscores import verified_dnp_player
from iphone_bot.paper_pick_pipeline import strict_player_name

FIXTURE = Path(__file__).resolve().parents[1] / "docs/verified_gamebook_inactives.json"
SOURCES = {"NBA_CDN_FINAL", "ESPN_FINAL"}


def load_gamebook_inactives(final_rows, path=FIXTURE):
    if not path.exists():
        return []
    output = []
    for game in json.loads(path.read_text())["games"]:
        day, gid = game["date"], game["game_id"]
        away, home = game["away"], game["home"]
        date = day.replace("-", "")
        expected_url = f"https://statsdmz.nba.com/pdfs/{date}/{date}_{away}{home}.pdf"
        if game["url"] != expected_url or not re.fullmatch(r"002\d{7}", gid):
            raise ValueError("Invalid official gamebook fixture identity")
        matching = [
            row for row in final_rows
            if row.get("date") == day and row.get("final_confirmed") is True
            and row.get("source") in SOURCES
            and (row.get("team"), row.get("opponent")) in ((away, home), (home, away))
        ]
        played = {
            (row["team"], strict_player_name(row.get("player")))
            for row in matching if row.get("dnp_final_verified") is not True
        }
        official_players = {
            (row["team"], strict_player_name(row.get("player")))
            for row in matching if row.get("dnp_final_verified") is not True
            and str(row.get("source_game_id")) == gid and row.get("source") == "NBA_CDN_FINAL"
        }
        if any(sum(t == team for t, _ in official_players) < 3 for team in (away, home)):
            continue
        explicit = {
            (row["team"], strict_player_name(row.get("player")))
            for row in matching if row.get("dnp_final_verified") is True
        }
        for entry in game["inactive"]:
            name, team, reason = entry["player"], entry["team"], entry["reason"]
            if team not in (away, home) or not strict_player_name(name) or not reason:
                raise ValueError("Invalid reviewed gamebook player identity")
            if (team, strict_player_name(name)) in played | explicit:
                continue
            row = verified_dnp_player(
                name, team, home if team == away else away, day, reason,
                "NBA_OFFICIAL_INACTIVE_CROSSCHECKED", gid,
            )
            if row:
                row["official_inactive_url"] = game["url"]
                if entry.get("corroboration_url"):
                    row["corroboration_url"] = entry["corroboration_url"]
                output.append(row)
    return output

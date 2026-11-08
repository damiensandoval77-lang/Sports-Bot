"""Offline PBP Stats request plan, NO API requests.

Based on dblackrun/pbpstats-api-code-examples/get-wowy-stats.ipynb.
Plans show provider fields for a target player and teammate both ON and
teammate OFF. Never call automatically: provider permission, a guaranteed
pregame date cutoff, and response mapping remain unverified.
"""
from urllib.parse import urlencode
from pathlib import Path

API="https://api.pbpstats.com/get-wowy-stats/nba"
SEASON="2026-27"
TYPE="Player"
TEAM_IDS={
"ATL":"1610612737","BOS":"1610612738","BKN":"1610612751",
"CHA":"1610612766","CHI":"1610612741","CLE":"1610612739",
"DAL":"1610612742","DEN":"1610612743","DET":"1610612765",
"GSW":"1610612744","HOU":"1610612745","IND":"1610612754",
"LAC":"1610612746","LAL":"1610612747","MEM":"1610612763",
"MIA":"1610612748","MIL":"1610612749","MIN":"1610612750",
"NOP":"1610612740","NYK":"1610612752","OKC":"1610612760",
"ORL":"1610612753","PHI":"1610612755","PHX":"1610612756",
"POR":"1610612757","SAC":"1610612758","SAS":"1610612759",
"TOR":"1610612761","UTA":"1610612762","WAS":"1610612764",
}

def request_plan(player_id,teammate_id,team,season=SEASON):
    """Return *descriptive* request params without making network requests."""
    pid=str(player_id);tid=str(teammate_id);team=str(team).upper()
    if (not pid.isdecimal() or not tid.isdecimal() or pid==tid
        or team not in TEAM_IDS or season!=SEASON):
        raise ValueError("Invalid canonical 2026-27 NBA player/teammate/team")
    common={"Season":SEASON,"SeasonType":"Regular Season",
            "TeamId":TEAM_IDS[team],"Type":TYPE,
            "0Exactly1OnFloor":pid}
    requests={
      "with":{**common,"1Exactly1OnFloor":tid},
      "without":{**common,"1Exactly1OffFloor":tid}
    }
    return {"status":"REQUEST_PLAN_ONLY_NETWORK_DISABLED",
        "endpoint":API,
        "team":team,"player_id":pid,"teammate_id":tid,
        "requests":requests,
        "requires_authorized_provider_access":True,
        "requires_verified_game_date_cutoff":True,
        "response_mapping_verified":False,
        "warning":"Do not fetch full-season after target tip or treat provider totals as pregame predictions. Validate on/off games and minutes before importer."}

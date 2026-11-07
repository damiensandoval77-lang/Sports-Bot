"""Optional, conservative archived NBA defender-matchup collector for V3 research.

Historical 2025-26 regular season ONLY, so the source predates the 2026-27
pregame evaluation period. This is a provider availability probe; NBA Stats
may block automated GitHub runners. Failure must not touch live AI models.
"""
import datetime as dt
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request

try:
    from .defender_matchup_v3 import ROOT, SOURCE,clean_matchup
except ImportError:
    from defender_matchup_v3 import ROOT,SOURCE,clean_matchup

STATUS=ROOT/"docs/defender_v3_source_status.json"
ENDPOINT="https://stats.nba.com/stats/leagueseasonmatchups"
SEASON="2025-26"
CUTOFF="2026-07-01T00:00:00Z"
COLUMNS=("OFF_PLAYER_ID","DEF_PLAYER_ID","PARTIAL_POSS",
         "MATCHUP_MIN","MATCHUP_FGA","MATCHUP_FGM")


def normalize_response(payload):
    """Accept only explicitly labeled LeagueSeasonMatchups resultSets."""
    sets=payload.get("resultSets",payload.get("resultSet"))
    if isinstance(sets,dict):sets=[sets]
    if not isinstance(sets,list):raise ValueError("missing NBA resultSets")
    for block in sets:
        if str(block.get("name","")).lower() not in ("seasonmatchups","leagueseasonmatchups"):
            continue
        headers=block.get("headers")
        rows=block.get("rowSet")
        if not isinstance(headers,list) or not isinstance(rows,list):
            raise ValueError("malformed matchups table")
        if len(headers)!=len(set(headers)) or not set(COLUMNS).issubset(headers):
            raise ValueError("NBA matchup columns missing")
        data=[dict(zip(headers,row)) for row in rows if isinstance(row,list) and len(row)==len(headers)]
        filtered=[r for r in data if clean_matchup(r) is not None]
        if not filtered:raise ValueError("no valid defender matchup observations")
        return filtered
    raise ValueError("NBA LeagueSeasonMatchups dataset not found")


def fetch(requester=None):
    if requester is not None:return normalize_response(requester())
    params={"LeagueID":"00","PerMode":"Totals","Season":SEASON,
            "SeasonType":"Regular Season","OffPlayerID":"",
            "DefPlayerID":"","OffTeamID":"","DefTeamID":""}
    url=ENDPOINT+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept":"application/json, text/plain, */*",
        "Referer":"https://www.nba.com/","Origin":"https://www.nba.com",
        "x-nba-stats-origin":"stats","x-nba-stats-token":"true"})
    with urllib.request.urlopen(req,timeout=12) as resp:
        data=json.load(resp)
    if not isinstance(data,dict):raise ValueError("NBA matchup result not an object")
    return normalize_response(data)


def main():
    report={"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":"MATCHUP_SOURCE_UNAVAILABLE",
        "requested_season":SEASON,
        "historical_source_through":CUTOFF,
        "live_model_unchanged":True,
        "source":ENDPOINT}
    try:
        rows=fetch()
        SOURCE.parent.mkdir(parents=True,exist_ok=True)
        SOURCE.write_text(json.dumps({"season":SEASON,"source_through":CUTOFF,
            "source":"NBA_LEAGUE_SEASON_MATCHUPS","rows":rows})+"\n")
        report.update(status="HISTORICAL_MATCHUPS_DOWNLOADED",valid_rows=len(rows))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        report.update(error_type=type(exc).__name__,
                      notice="Matchup source not proven on GitHub runner; no defender estimates generated.")
    STATUS.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True),flush=True)


if __name__=="__main__":main()

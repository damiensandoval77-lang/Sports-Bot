"""Refresh 2026-27 NBA player recent form from a public versioned CSV export.

Source: xtheredshirtx/fanduel-player-data, NBA/csv. The project states these
are third-party NBA box-score extracts; not associated with FanDuel.
This is observational player form, not AI probabilities or wagers.
"""
import csv
import datetime as dt
import io
import json
import pathlib
import re
import statistics
import urllib.request
from collections import defaultdict

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/current_form.json"
API="https://api.github.com/repos/xtheredshirtx/fanduel-player-data/contents/NBA/csv"
RAW="https://raw.githubusercontent.com/xtheredshirtx/fanduel-player-data/main/NBA/csv/"
PATTERN=re.compile(r"^NBA_players_game_log_2026-27_as_of_(\d{4}-\d{2}-\d{2})\.csv$")
HEADERS={"User-Agent":"Sports-Bot-NBA-Research/1.0","Accept":"application/vnd.github+json"}

def fetch(url):
    request=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(request,timeout=30) as response:
        return response.read()

def number(value):
    try:
        f=float(str(value).strip())
        return f if f>=0 else None
    except (ValueError,TypeError):
        return None

def main():
    listing=json.loads(fetch(API))
    versions=[]
    for item in listing:
        match=PATTERN.fullmatch(item.get("name",""))
        if match:
            versions.append((dt.date.fromisoformat(match.group(1)),item["name"]))
    if not versions:
        raise ValueError("No 2026-27 public game logs found")
    version,filename=max(versions)
    today=dt.datetime.now(dt.timezone.utc).date()
    if (today-version).days>5:
        raise ValueError(f"Source export is stale: {version} (more than 5 days)")
    print("Downloading public NBA player logs:",filename,flush=True)
    reader=csv.DictReader(io.StringIO(fetch(RAW+filename).decode("utf-8-sig")))
    required={"Date","Player","ID","Team","Season","Points","Rebounds","Assists","Minutes"}
    missing=required-set(reader.fieldnames or [])
    if missing:
        raise ValueError("CSV schema changed: missing "+str(sorted(missing)))
    by_player=defaultdict(dict)
    rejected=0
    latest=None
    for row in reader:
        try:
            date=dt.date.fromisoformat(str(row["Date"]).strip()[:10])
        except ValueError:
            rejected+=1
            continue
        if date>today or date<dt.date(2026,10,20):
            rejected+=1
            continue
        player=str(row.get("Player","")).strip()
        ident=str(row.get("ID","")).strip()
        team=str(row.get("Team","")).strip()
        season=str(row.get("Season","")).strip()
        if not ident or not player or not team or season not in ("2026-27","2026"):
            rejected+=1
            continue
        pts=number(row.get("Points"))
        reb=number(row.get("Rebounds"))
        ast=number(row.get("Assists"))
        mins=number(row.get("Minutes"))
        if any(v is None for v in (pts,reb,ast,mins)) or mins<1:
            rejected+=1
            continue
        game={"player":player,"id":ident,"team":team,"date":date.isoformat(),
              "PTS":pts,"REB":reb,"AST":ast,"PRA":pts+reb+ast,"MIN":mins}
        # This dataset is one player per date; reject conflicting duplicate records.
        previous=by_player[ident].get(date)
        if previous and (previous["PTS"],previous["REB"],previous["AST"])!=(pts,reb,ast):
            raise ValueError(f"Conflicting duplicate for player id {ident} on {date}")
        by_player[ident][date]=game
        latest=max(latest,date) if latest else date
    if not latest or (today-latest).days>5:
        raise ValueError("Latest player game is too old for current dashboard")
    players=[]
    for ident,dates in by_player.items():
        games=[dates[k] for k in sorted(dates)]
        if len(games)<3:
            continue
        recent=games[-1]
        result={"player":recent["player"],"player_id":ident,"team":recent["team"],
                "latest_game":recent["date"],"games":len(games),"metrics":{}}
        for stat in ("PTS","REB","AST","PRA","MIN"):
            values=[g[stat] for g in games]
            result["metrics"][stat]={
                "l3":round(statistics.mean(values[-3:]),2),
                "l5":round(statistics.mean(values[-5:]),2) if len(values)>=5 else None,
                "l10":round(statistics.mean(values[-10:]),2) if len(values)>=10 else None,
                "season":round(statistics.mean(values),2)}
        players.append(result)
    players.sort(key=lambda x:x["player"])
    total=sum(len(v) for v in by_player.values())
    if len(players)<80 or total<1000:
        raise ValueError(f"Insufficient observations: {len(players)} players, {total} player-games")
    payload={"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_version":str(version),"latest_game_date":str(latest),
        "season":"2026-27","completed_games":None,"box_score_games":None,
        "failed_game_count":rejected,"observed_player_games":total,
        "player_count":len(players),
        "source":"Public NBA player-game CSV published by xtheredshirtx/fanduel-player-data",
        "source_url":"https://github.com/xtheredshirtx/fanduel-player-data/tree/main/NBA/csv",
        "is_ai":False,"is_prizepicks":False,
        "disclaimer":"Observed completed-game statistics only. Public third-party data may lag official NBA corrections. L5/L10 need five/ten games. Not AI projections, PrizePicks lines, or calibrated betting probabilities.",
        "players":players}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2)+"\n")
    print(f"Published {len(players)} players from {total} current-season player-games; latest game {latest}; rejected {rejected}",flush=True)

if __name__=="__main__":
    main()

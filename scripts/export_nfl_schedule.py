"""Publish the full NFL schedule independently from odds and AI forecasts."""
import csv
import io
import json
import os
import tempfile
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

YEAR=2026
SOURCE="https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
OUTPUT=Path("docs/nfl/data/schedule_2026.json")

def run():
    request=urllib.request.Request(SOURCE,headers={"User-Agent":"DamesPicks-NFLSchedule/1.0"})
    with urllib.request.urlopen(request,timeout=75) as response:
        data=response.read().decode("utf-8-sig")
    source=list(csv.DictReader(io.StringIO(data)))
    games=[]
    for row in source:
        stage=(row.get("season_type") or row.get("game_type") or "").upper()
        if row.get("season")!=str(YEAR) or stage!="REG":
            continue
        when=datetime.strptime(row["gameday"]+" "+row["gametime"],"%Y-%m-%d %H:%M")
        kickoff=when.replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
        def score(field):
            value=row.get(field) or ""
            return int(float(value)) if value.strip() else None
        away=score("away_score")
        home=score("home_score")
        completed=away is not None and home is not None
        status="final" if completed else ("started_unconfirmed" if kickoff<=datetime.now(timezone.utc) else "scheduled")
        games.append({"game_id":row["game_id"],"season":YEAR,"week":int(row["week"]),
                      "kickoff_utc":kickoff.isoformat(),
                      "home":row["home_team"],"away":row["away_team"],
                      "home_score":home,"away_score":away,
                      "status":status,"has_lines":False,"has_projections":False})
    games.sort(key=lambda x:(x["week"],x["kickoff_utc"],x["game_id"]))
    if len(games)!=272 or len({g["game_id"] for g in games})!=272:
        raise RuntimeError(f"Refusing incomplete/duplicated NFL 2026 season: {len(games)} vs 272")
    if len({x["week"] for x in games})!=18:
        raise RuntimeError("NFL schedule does not cover 18 regular-season weeks")
    payload={"season":YEAR,"generated_at":datetime.now(timezone.utc).isoformat(),
             "game_count":len(games),"source":"nflverse/nfldata games.csv",
             "games":games,"coverage":{"scheduled_games":len(games),
                                      "note":"Availability of PrizePicks props tracked separately in NFL dashboard"}}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    # Ignore timestamp-only changes so routine runs do not cause Pages deploy churn.
    if OUTPUT.exists():
        previous=json.loads(OUTPUT.read_text())
        previous.pop("generated_at",None)
        comparable=dict(payload)
        comparable.pop("generated_at",None)
        if previous==comparable:
            print("NFL schedule unchanged; no commit")
            return
    with tempfile.NamedTemporaryFile("w",dir=str(OUTPUT.parent),delete=False,encoding="utf-8") as tmp:
        json.dump(payload,tmp,separators=(",",":"))
        tmp.write("\n")
        filename=tmp.name
    os.replace(filename,OUTPUT)
    print(f"Published all {len(games)} NFL games in {len(set(x['week'] for x in games))} weeks")

if __name__=="__main__":
    run()

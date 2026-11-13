"""Fetch source-observed 2026-27 NBA team estimated defensive ratings.

Independent CC-BY-4.0 data source: BoxScore Lab. Ratings are estimated
points allowed / 100 possessions; they are NOT equivalent to PPG allowed.
Every run preserves source UTC retrieval timestamp, CSV digest, original
column names and source URL. No historical-pick retroactive as-of claims.
"""
import csv
import hashlib
import io
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE="https://www.boxscorelab.com/downloads/2026-27-team-standings.csv"
EXPECTED_SEASON="2026-27"
TEAMS={
    "ATL":"ATLANTA HAWKS","BOS":"BOSTON CELTICS","BKN":"BROOKLYN NETS",
    "CHA":"CHARLOTTE HORNETS","CHI":"CHICAGO BULLS","CLE":"CLEVELAND CAVALIERS",
    "DAL":"DALLAS MAVERICKS","DEN":"DENVER NUGGETS","DET":"DETROIT PISTONS",
    "GSW":"GOLDEN STATE WARRIORS","HOU":"HOUSTON ROCKETS","IND":"INDIANA PACERS",
    "LAC":"LOS ANGELES CLIPPERS","LAL":"LOS ANGELES LAKERS","MEM":"MEMPHIS GRIZZLIES",
    "MIA":"MIAMI HEAT","MIL":"MILWAUKEE BUCKS","MIN":"MINNESOTA TIMBERWOLVES",
    "NOP":"NEW ORLEANS PELICANS","NYK":"NEW YORK KNICKS","OKC":"OKLAHOMA CITY THUNDER",
    "ORL":"ORLANDO MAGIC","PHI":"PHILADELPHIA 76ERS","PHX":"PHOENIX SUNS",
    "POR":"PORTLAND TRAIL BLAZERS","SAC":"SACRAMENTO KINGS",
    "SAS":"SAN ANTONIO SPURS","TOR":"TORONTO RAPTORS",
    "UTA":"UTAH JAZZ","WAS":"WASHINGTON WIZARDS"
}
BY_NAME={name:abbr for abbr,name in TEAMS.items()}
BY_NAME["LA CLIPPERS"]="LAC"
BY_NAME["NEW ORLEANS PELICANS"]="NOP"
RATING_FIELDS=("def_rating_est","defensive_rating_est","drtg_est","estimated_defensive_rating",
               "estimated_def_rating","def_rating","defensive_rating","drtg")
PACE_FIELDS=("pace","pace_est","estimated_pace","pace_estimated")
TEAM_FIELDS=("team_abbr","team_abbreviation","team_tricode","team","abbreviation","team_name","name")
SEASON_FIELDS=("season","season_id","season_year")
GAMES_FIELDS=("gp","games","games_played")
def norm(k):
    return str(k).strip().lower().replace(" ","_").replace("-","_").replace("%","pct")
def field(row,choices):
    for name in choices:
        if name in row and str(row[name]).strip():
            return row[name],name
    return None,None
def team(raw):
    key=str(raw or "").upper().strip()
    return key if key in TEAMS else BY_NAME.get(key)
def val(raw,lo,hi):
    try:
        v=float(str(raw).replace(",",""))
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and lo<=v<=hi else None
def parse_csv(csv_text, *, captured_at, source_url=SOURCE):
    if not csv_text.strip():raise ValueError("empty downloaded CSV")
    downloaded=datetime.fromisoformat(captured_at.replace("Z","+00:00"))
    if downloaded.tzinfo is None:raise ValueError("source capture timezone absent")
    reader=csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:raise ValueError("CSV header absent")
    actual_fields=tuple(reader.fieldnames)
    data={}
    invalid=[]
    for raw in reader:
        row={norm(k):v for k,v in raw.items() if k}
        season,_=field(row,SEASON_FIELDS)
        if season is not None and season not in ("2026-27","2026","22026"):raise ValueError("wrong season")
        raw_team,key=field(row,TEAM_FIELDS)
        abbr=team(raw_team)
        if not abbr:
            invalid.append("UNKNOWN_TEAM");continue
        drtg,col=field(row,RATING_FIELDS)
        drtg=val(drtg,70,160)
        games,col_games=field(row,GAMES_FIELDS)
        games=val(games,1,100)
        pace,col_pace=field(row,PACE_FIELDS)
        pace=val(pace,75,125) if pace is not None else None
        if drtg is None or games is None:
            invalid.append("MISSING_VALID_RATING_OR_GAMES");continue
        if abbr in data:raise ValueError("duplicate team rating")
        data[abbr]={"team":abbr,"defensive_rating":drtg,"metric":"ESTIMATED_POINTS_ALLOWED_PER_100_POSSESSIONS",
                    "played_games":int(games),"pace":pace,"rating_field":col,
                    "pace_field":col_pace,"source":source_url,
                    "observed_at":captured_at}
    if len(data)!=30:
        raise ValueError("incomplete NBA rating file: "+str(len(data))+
                         " teams; headers "+str(actual_fields)+"; errors "+str(invalid[:5]))
    mean_rating=sum(x["defensive_rating"] for x in data.values())/30
    for v in data.values():v["league_defensive_rating"]=round(mean_rating,4)
    return {"status":"SOURCED_ESTIMATED_DEF_RATING_RESEARCH","captured_at":captured_at,
            "season":EXPECTED_SEASON,"source_url":source_url,
            "source_license":"CC BY 4.0; attribution BoxScore Lab, boxscorelab.com",
            "sha256":hashlib.sha256(csv_text.encode()).hexdigest(),
            "csv_fields":list(actual_fields),"teams":data,"team_count":30,
            "production_approved":False,
            "historical_pretip_feature_backfill":False,
            "note":"Estimated defensive rating is descriptive and is not a calibrated player prop probability."}
def fetch(*, request=None, captured_at=None):
    if request is None:
        def request(url):
            req=urllib.request.Request(url,headers={"User-Agent":"Sports-Bot/1.0 research provenance"})
            with urllib.request.urlopen(req,timeout=15) as response:
                return response.read().decode("utf-8-sig")
    at=captured_at or datetime.now(timezone.utc).isoformat()
    return parse_csv(request(SOURCE),captured_at=at)
def main():
    data=fetch()
    out=Path("defensive-rating-research.json")
    out.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":data["status"],"teams":data["team_count"],
                      "captured_at":data["captured_at"],"sample_columns":data["csv_fields"],
                      "production_approved":False}))
if __name__=="__main__":main()

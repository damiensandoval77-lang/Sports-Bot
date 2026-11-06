"""One-game DunkAPI historical bookmaker prop importer.

Uses the documented REST data envelope. The workflow requires explicit
manual invocation and a 20-credit estimate cap. Rejects post-tipoff quotes.
"""
import csv
import datetime as dt
import json
import os
import re
import pandas as pd
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/nba/odds/observed_props.csv"
BASE="https://mcp.dunkapi.com/v1/get_player_props"
FIELDS=["game_date","player_name","market","bookmaker","line","over_odds","under_odds","captured_at","event_start","game","source"]
MARKETS={"player_points":"PTS","player_rebounds":"REB","player_assists":"AST","player_points_rebounds_assists":"PRA"}
GAME_ID=os.environ.get("DUNK_GAME_ID","401810837").strip()
CREDIT_LIMIT=int(os.environ.get("DUNK_CREDIT_LIMIT","20"))

def request(key,body):
    req=Request(BASE,json.dumps(body).encode("utf-8"),
                headers={"Content-Type":"application/json","x-api-key":key},
                method="POST")
    try:
        with urlopen(req,timeout=45) as response:
            result=json.load(response)
    except HTTPError as e:
        print(f"Provider returned HTTP {e.code}, no API key disclosed.",flush=True)
        raise
    if not isinstance(result,dict) or not isinstance(result.get("data"),dict):
        raise ValueError("Unexpected DunkAPI REST response envelope")
    return result["data"]

def timestamp(s):
    if not s:return None
    val=dt.datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if val.tzinfo is None:return None
    return val.astimezone(dt.timezone.utc)

def main():
    key=os.environ.get("DUNKAPI_KEY","").strip()
    if not key:raise SystemExit("DUNKAPI_KEY GitHub secret missing")
    if CREDIT_LIMIT<0 or CREDIT_LIMIT>20:raise SystemExit("Credit cap must be 0..20")
    if not GAME_ID.isdigit():raise SystemExit("Game ID should contain digits only")
    # Fail closed unless a provider game ID is verified against NBA box-score ID.
    verified_ids={"401810837":("0022500982","2026-03-15")}
    if GAME_ID not in verified_ids:
        raise SystemExit("Game ID not yet independently verified; no paid import should be requested.")
    nba_game_id,verified_date=verified_ids[GAME_ID]
    box_path=ROOT/"data/nba/raw/raw_game_logs.csv"
    if not box_path.exists():
        raise SystemExit("NBA box-score archive missing; cannot validate player/game identity.")
    boxes=pd.read_csv(box_path,dtype={"GAME_ID":"string"},low_memory=False)
    subset=boxes.loc[(boxes["GAME_ID"].astype(str)==nba_game_id)&(boxes["GAME_DATE"].astype(str)==verified_date)]
    def normalize_name(x):return re.sub(r"[^a-z0-9]","",str(x).casefold())
    allowed={normalize_name(n) for n in subset["PLAYER_NAME"].dropna()}
    if len(allowed)<8:
        raise SystemExit("Verified box-score roster missing or unexpectedly small; refusing import.")
    print("Verified NBA game",nba_game_id,"with",len(allowed),"player names")
    body={"game_id":GAME_ID,"league":"nba","snapshot_type":"closing"}
    estimate=request(key,{**body,"estimate_only":True})
    credits=estimate.get("credits")
    print("Estimate for game",GAME_ID,":",credits,"credits",flush=True)
    if not isinstance(credits,(int,float)) or credits>CREDIT_LIMIT:
        raise SystemExit("Cost estimate missing or over configured limit; purchase aborted.")
    if credits<=0:
        raise SystemExit("Unusual cost estimate; purchase aborted.")
    # One paid provider request only. No fallback that could spend extra credits.
    result=request(key,body)
    props=result.get("props",[])
    if not isinstance(props,list):
        raise ValueError("Invalid props payload")
    print("Provider returned",len(props),"prop records",flush=True)
    new=[]
    rejected={"missing":0,"post_tipoff":0,"bad_price":0,"market":0,"wrong_game_player":0}
    for p in props:
        market=MARKETS.get(p.get("market"))
        if market is None:
            rejected["market"]+=1
            continue
        captured=timestamp(p.get("captured_at"))
        start=timestamp(p.get("scheduled_start"))
        if not captured or not start:
            rejected["missing"]+=1
            continue
        if captured>=start:
            rejected["post_tipoff"]+=1
            continue
        try:
            line=float(p["line"])
            over=int(p["over_odds"])
            under=int(p["under_odds"])
        except (ValueError,TypeError,KeyError):
            rejected["bad_price"]+=1
            continue
        if line%1 != .5 or not ((over<=-100 or over>=100) and (under<=-100 or under>=100)):
            rejected["bad_price"]+=1
            continue
        name=str(p.get("player_name","")).strip()
        book=str(p.get("bookmaker","")).strip()
        date=str(p.get("game_date","")).strip()
        if not name or not book or not date:
            rejected["missing"]+=1
            continue
        if date!=verified_date or normalize_name(name) not in allowed:
            rejected["wrong_game_player"]+=1
            continue
        new.append({
            "game_date":date,"player_name":name,"market":market,
            "bookmaker":book,"line":line,"over_odds":over,"under_odds":under,
            "captured_at":captured.isoformat(),"event_start":start.isoformat(),
            "game":str(p.get("game_id",GAME_ID)),"source":"dunkapi-historical"})
    print("Validated",len(new),"quotes; rejected",rejected,flush=True)
    if not new:
        print("No records had verifiable pre-tipoff captured_at AND scheduled_start. No CSV created.",flush=True)
        return
    old=[]
    if OUT.exists():
        with OUT.open(newline="") as fh:old=list(csv.DictReader(fh))
    def identity(x):
        return (x["game_date"],x["player_name"],x["market"],x["bookmaker"],
                str(float(x["line"])),x["captured_at"],x["event_start"])
    combined={identity(x):x for x in old}
    combined.update({identity(x):x for x in new})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",newline="") as fh:
        writer=csv.DictWriter(fh,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(combined.values(),key=lambda x:(x["game_date"],x["player_name"],x["market"])))
    print("Archived",len(new),"verified pre-tipoff quotes; total",len(combined),flush=True)

if __name__=="__main__":
    main()

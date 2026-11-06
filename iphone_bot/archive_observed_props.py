"""Archive real observed NBA bookmaker prop quotes from the existing dashboard feed.

Quotes are PRE-GAME and timestamped. This is not a backfill of historical odds.
Do not equate sportsbook odds with PrizePicks lines.
"""
import csv
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/data.json"
DEST=ROOT/"data/nba/odds/observed_props.csv"
FIELDS=["game_date","player_name","market","bookmaker","line","over_odds","under_odds",
        "captured_at","event_start","game","source"]
MARKETS={"Points":"PTS","Rebounds":"REB","Assists":"AST",
         "Points Rebounds Assists":"PRA"}
def iso(s):
    return dt.datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(dt.timezone.utc)
def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    obj=json.loads(SOURCE.read_text())
    if not obj.get("is_live"):
        print("Skipping: feed is not live");return
    capture=iso(obj["updated_at"])
    seen={}
    for p in obj.get("picks",[]):
        market=MARKETS.get(p.get("stat"))
        if market is None or not p.get("player") or p.get("line") is None: continue
        start=iso(p["start"])
        if capture>=start: continue
        # Actual NBA calendar date in US Eastern time, not the UTC date.
        game_date=start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        book=str(p.get("source","")).strip()
        key=(game_date,p["player"].strip(),market,book,float(p["line"]),start.isoformat(),p.get("game",""))
        row=seen.setdefault(key,{"game_date":game_date,"player_name":key[1],"market":market,
                    "bookmaker":book,"line":float(p["line"]),"over_odds":"",
                    "under_odds":"","captured_at":capture.isoformat(),
                    "event_start":start.isoformat(),"game":p.get("game",""),"source":"the-odds-api-live-snapshot"})
        side=p.get("direction")
        if side in ("More","Less"):
            try:
                price=int(p["odds"])
            except (ValueError,TypeError): continue
            if price==0: continue
            row["over_odds" if side=="More" else "under_odds"]=price
    rows=[r for r in seen.values() if r["over_odds"]!="" and r["under_odds"]!=""]
    if not rows:
        print("No complete eligible pregame price pairs");return
    old=[]
    if DEST.exists():
        with DEST.open(newline="") as f:
            old=list(csv.DictReader(f))
    # Preserve earlier observations, and replace exactly duplicate quote snapshots.
    def ident(r):
        return (r["game_date"],r["player_name"],r["market"],r["bookmaker"],
                str(float(r["line"])),r["captured_at"],r["event_start"])
    keyed={ident(r):r for r in old}
    keyed.update({ident(r):r for r in rows})
    DEST.parent.mkdir(parents=True,exist_ok=True)
    with DEST.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(keyed.values(),key=lambda x:(x["game_date"],x["player_name"],x["market"],x["captured_at"])))
    print(f"Archived {len(rows)} valid pregame two-sided quotes; total {len(keyed)}")
if __name__=="__main__": main()

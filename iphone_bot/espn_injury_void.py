"""Evidence-only ESPN final-box + injury-list DNP exclusions; never turn a DNP into a loss."""
import datetime as dt
import json
import re
import unicodedata
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/lagged_matchup_all_market_ledger.json"
OUTPUT=ROOT/"docs/espn_injury_void_ledger.json"
SOURCE="ESPN_FINAL_BOX_ABSENT_INJURY_LISTED"
BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

def norm(name):
    s=unicodedata.normalize("NFKD",str(name or "")).encode("ascii","ignore").decode().lower()
    return re.sub("[^a-z]","",re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?","",s))

def stamp(raw):
    try:
        v=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        return v if v.tzinfo else v.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError): return None

def matchup(competitors):
    teams={c.get("homeAway"):c.get("team",{}).get("displayName") for c in competitors}
    return f"{teams['away']} @ {teams['home']}" if teams.get("away") and teams.get("home") else None

def facts(summary,event_id):
    comp=(summary.get("header",{}).get("competitions") or [{}])[0]
    if comp.get("status",{}).get("type",{}).get("completed") is not True:return None
    teams=summary.get("boxscore",{}).get("players") or []
    if len(teams)!=2 or not all(any(block.get("athletes") for block in team.get("statistics",[])) for team in teams):return None
    played=set()
    for team in teams:
        for block in team.get("statistics",[]):
            for p in block.get("athletes",[]):
                if not p.get("didNotPlay") and p.get("stats"):
                    played.add(norm(p.get("athlete",{}).get("displayName")))
    injured={}
    for team in summary.get("injuries",[]):
        for entry in team.get("injuries",[]):
            name=norm(entry.get("athlete",{}).get("displayName"))
            if name:injured[name]=entry.get("status") or entry.get("type",{}).get("description") or "listed"
    return {"game":matchup(comp.get("competitors") or []),"played":played,"injured":injured,"event_id":str(event_id)}

def identify(r):
    return tuple(str(r.get(x) or "") for x in ("player_id","team","game","start","stat"))

def decide(r,f):
    if not f or f["game"]!=r.get("game"):return None
    name=norm(r.get("player"))
    if not name or name in f["played"] or name not in f["injured"]:return None
    return {"status":"EXCLUDED_VERIFIED_DNP","player_id":str(r.get("player_id")),
            "player":r.get("player"),"team":r.get("team"),"game":r.get("game"),
            "start":r.get("start"),"stat":r.get("stat"),"captured_at":r.get("captured_at"),
            "projection":r.get("projection"),"actual":None,"final_source":SOURCE,
            "source_game_id":f["event_id"],"verified_dnp_reason":"ESPN complete final box: no playing stat line; injury list: "+str(f["injured"][name])}

def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"DamesPicks-FinalDNP/1.0"}),timeout=20) as r:
        return json.loads(r.read())

def run(rows,existing,now,reader=fetch):
    found={identify(x) for x in existing}
    cache={}
    additions=[]
    for r in rows:
        start=stamp(r.get("start"))
        if r.get("grade")!="PENDING" or not start or now-start<dt.timedelta(hours=4) or identify(r) in found:continue
        key=(r.get("game"),r.get("start"))
        if key not in cache:
            cache[key]=None
            try:
                day=start.astimezone(ZoneInfo("America/New_York")).strftime("%Y%m%d")
                board=reader(f"{BASE}/scoreboard?dates={day}&limit=100")
                game=next((e for e in board.get("events",[]) if matchup(e["competitions"][0]["competitors"])==key[0]),None)
                if game:cache[key]=facts(reader(f"{BASE}/summary?event={game['id']}"),game["id"])
            except (KeyError,IndexError,TypeError,ValueError,TimeoutError,OSError) as e:
                print("Unverified ESPN DNP (leave pending):",key,str(e))
        item=decide(r,cache[key])
        if item:additions.append(item);found.add(identify(item))
    return additions

def main():
    original=json.loads(LEDGER.read_text()).get("records",[])
    previous=json.loads(OUTPUT.read_text()).get("records",[]) if OUTPUT.exists() else []
    additions=run(original,previous,dt.datetime.now(dt.timezone.utc))
    OUTPUT.write_text(json.dumps({"version":1,"source":SOURCE,"records":previous+additions},indent=2)+"\n")
    print("ESPN injury DNP records added:",len(additions),"total:",len(previous)+len(additions))

if __name__=="__main__":main()

"""Persist verified pretip PrizePicks observations for later live tracking.

Not predictions, not bets, and never populated by post-tip source observations.
No provider API requests. Every record is independently source-linked.
"""
import datetime as dt
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/prizepicks_pregame_line_archive.json"
SITE=ROOT/"docs/prizepicks_site.json"
STATUS="VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE"
SOURCE="independent_prizepicksapi_com"
TIERS={"standard","goblin","demon"}
STATS={"PTS","REB","AST","PRA"}

def moment(value):
    try:
        x=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return x.astimezone(dt.timezone.utc) if x.tzinfo else None
    except (TypeError,ValueError,OverflowError):
        return None

def market_identity(q):
    return tuple(q[k] for k in ("player","team","game","stat","starts_at","tier"))

def identity(q):
    # Retain genuine historical price versions instead of overwriting a frozen
    # line when the same provider market moves before tipoff.
    return market_identity(q)+(q["line"],)

def safe_row(q):
    if not isinstance(q,dict) or q.get("source")!=SOURCE or q.get("is_demo") is not False:
        return False
    if not all(isinstance(q.get(k),str) and q[k].strip() for k in
               ("id","player","team","game","starts_at","observed_at","source_generated_at")):
        return False
    if q.get("stat") not in STATS or q.get("tier") not in TIERS:
        return False
    if q.get("more_tier")!=q["tier"] or q.get("less_tier")!=q["tier"]:
        return False
    line=q.get("line")
    if type(line) not in (int,float) or not math.isfinite(line) or not 0<=line<=200:
        return False
    start,observed,generated=map(moment,(q["starts_at"],q["observed_at"],q["source_generated_at"]))
    return bool(start and observed and generated and observed<=generated<start and
                (generated-observed).total_seconds()<=5400 and
                (start-generated).total_seconds()<=86400)  # Valid quotes up to 24h pretip

def build(site,old=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    previous=(old or {}).get("quotes") or []
    saved={identity(q):q for q in previous if safe_row(q) and
           moment(q["starts_at"])>=now-dt.timedelta(days=14)}
    if site.get("status")== "LIVE_THIRD_PARTY_PRIZEPICKS_LINES" and site.get("source")==SOURCE:
        timestamp=site.get("generated_at")
        generated=moment(timestamp)
        if generated and generated<=now+dt.timedelta(minutes=10):
            current={}
            for row in site.get("board_offers") or []:
                if not isinstance(row,dict):continue
                q={k:row.get(k) for k in ("id","player","team","game","stat",
                  "line","starts_at","observed_at","more_tier","less_tier","source","is_demo")}
                q["tier"]=q["more_tier"]
                q["source_generated_at"]=timestamp
                if not safe_row(q):continue
                key=market_identity(q)
                current.setdefault(key,[]).append(q)
            for key,offers in current.items():
                # Ambiguous simultaneous quotes cannot be promoted as a single line.
                if len({q["line"] for q in offers})!=1:continue
                q=max(offers,key=lambda x:x["observed_at"])
                # Each distinct standard price is a separate historical receipt.
                # Keep the *earliest* captured observation for its original price.
                price_key=identity(q)
                prior=saved.get(price_key)
                if prior is None or moment(q["observed_at"])<moment(prior["observed_at"]):
                    saved[price_key]=q
    rows=sorted(saved.values(),key=lambda q:(q["starts_at"],q["game"],q["player"],q["stat"],q["tier"],q["line"],q["observed_at"]))
    return {"status":STATUS,"generated_at":now.isoformat(),"quotes":rows,
            "count":len(rows),"note":"Observed before tipoff; not frozen AI betting picks. Tier shown separately."}

def main():
    provider=json.loads(SITE.read_text())
    try: prior=json.loads(OUT.read_text())
    except (OSError,ValueError):prior={}
    output=build(provider,prior)
    OUT.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":"))+"\n")
    print("Verified historical pretip quotes:",output["count"])

if __name__=="__main__":main()

"""Audit original-residual simulation probabilities against Combined AI direction.

The original residual estimate is only a PROXY for a Combined AI decision, not
a calibrated Combined AI probability. Freeze the quote-specific proxy BEFORE
tipoff; do not reconstruct from subsequently altered AI boards. Score only
settled, independently selected earliest market quotes. No in-sample
recalibration, no live probability changes.
"""
import json
import math
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
try:
    from .paper_pick_pipeline import utc
except ImportError:
    from paper_pick_pipeline import utc

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"docs/combined_probability_audit.json"
BINS=((0,.5),(.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.0000000001))
STATS=("PTS","REB","AST","PRA")
METHOD="ORIGINAL_RESIDUAL_PROXY_FOR_COMBINED_DIRECTION_UNCALIBRATED"

def number(value):
    if isinstance(value,bool):return None
    try:
        value=float(value)
    except (ValueError,TypeError):return None
    return value if math.isfinite(value) else None

def locked(records):
    grouped=defaultdict(list)
    excluded=Counter()
    for row in records:
        if row.get("status")!="SETTLED":
            excluded["unsettled"]+=1;continue
        try:
            start=utc(row["event_start"])
            capture=utc(row["captured_at"])
            if capture>=start:
                excluded["captured_after_start"]+=1;continue
            p=number(row.get("combined_probability_proxy_estimate"))
            line=number(row.get("line"))
            actual=number(row.get("actual"))
            projection=number(row.get("combined_projection"))
            if p is None:
                excluded["no_pregame_frozen_proxy"]+=1;continue
            if (not 0<=p<=1 or line is None or actual is None or projection is None):
                excluded["invalid_quote"]+=1;continue
            side="OVER" if projection>line else "UNDER" if projection<line else None
            if (side is None or side!=row.get("combined_probability_proxy_side") or
                side!=row.get("side") or
                row.get("combined_probability_proxy_method")!=METHOD):
                excluded["wrong_side_or_method"]+=1;continue
            if actual==line:
                excluded["push"]+=1;continue
            key=(start.isoformat(),str(row["player_id"]),str(row["market"]))
            grouped[key].append((capture,str(row.get("bookmaker","")).casefold(),line,row,p,side))
        except (ValueError,KeyError,TypeError):
            excluded["invalid_identity"]+=1
    selected=[]
    for key,items in sorted(grouped.items()):
        capture,book,line,row,p,side=min(items,key=lambda x:(x[0],x[1],x[2]))
        actual=float(row["actual"])
        selected.append({"date":utc(row["event_start"]).date().isoformat(),
            "market":row["market"],"probability":p,
            "won":int((actual>line)==(side=="OVER")),
            "player_id":str(row["player_id"]),"game":row.get("game"),
            "event_start":utc(row["event_start"]).isoformat()})
    return selected,dict(excluded)

def wilson(wins,total,z=1.96):
    if total==0:return None
    p=wins/total
    den=1+z*z/total
    center=(p+z*z/(2*total))/den
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [round(max(0,center-half),4),round(min(1,center+half),4)]

def describe(items):
    n=len(items)
    wins=sum(x["won"] for x in items)
    return {"sample_size":n,"wins":wins,"losses":n-wins,
        "distinct_game_dates":len({x["date"] for x in items}),
        "observed_hit_rate":round(wins/n,4) if n else None,
        "mean_proxy_probability":round(sum(x["probability"] for x in items)/n,4) if n else None,
        "calibration_gap":round((wins-sum(x["probability"] for x in items))/n,4) if n else None,
        "brier_score":round(sum((x["probability"]-x["won"])**2 for x in items)/n,4) if n else None,
        "observed_hit_rate_wilson95":wilson(wins,n)}

def report(records):
    items,excluded=locked(records)
    bands=[]
    for lo,hi in BINS:
        subset=[x for x in items if lo<=x["probability"]<hi]
        bands.append({"label":f"{int(lo*100)}–{min(100,int(hi*100))}%",
                      "lower":lo,"upper":min(hi,1.),**describe(subset),
                      "reliable":len(subset)>=100 and len({x["date"] for x in subset})>=10})
    stats={stat:describe([x for x in items if x["market"]==stat]) for stat in STATS}
    # Entire dates are held out; no fitting or performance claims on same-day data.
    return {"status":"UNVALIDATED_COMBINED_DIRECTION_RESIDUAL_PROXY",
        "probability_kind":"ORIGINAL_AI_RESIDUAL_SIMULATION_FOR_COMBINED_CHOSEN_SIDE",
        "is_calibrated":False,"show_as_verified_confidence":False,
        "minimum_per_band":100,"minimum_distinct_dates_per_band":10,
        "overall":describe(items),"bands":bands,"by_stat":stats,
        "excluded":excluded,"prospective_validation_required":True,
        "limitations":[
            "This is the ORIGINAL AI residual probability for the direction selected by Combined AI, not a calibrated Combined AI simulation.",
            "A probability must be frozen pregame for the exact book and line; missing historical probabilities are never reconstructed.",
            "A single game's markets and player statistics are strongly correlated.",
            "Wilson intervals are approximate and do not correct cross-player or within-game correlation.",
            "Observed win rates are descriptive. No adjustment is deployed or justified from small buckets.",
            "Verified probability calibration requires future holdout dates and pre-registered fit rules." ]}

def main():
    records=json.loads(LEDGER.read_text()).get("records",[])
    value=report(records)
    value["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(value,indent=2)+"\n")
    print("COMBINED PROXY PROBABILITY AUDIT:",json.dumps({
        "overall":value["overall"],"excluded":value["excluded"]},sort_keys=True),flush=True)

if __name__=="__main__":main()

"""Audit arithmetic consistency of frozen pretip player projections.

A PRA estimate for a player's game must be explainable relative to its
points+rebounds+assists components. This is a feed-integrity diagnostic,
NOT proof of better prop hit rate. Never alter locked forecasts.
"""
import json
import math
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"docs/ai_no_line_pregame_archive.json"
CURRENT=ROOT/"docs/ai_projection_fallback.json"
OUTPUT=ROOT/"docs/cross_market_coherence.json"
STATS=("PTS","REB","AST","PRA")
# Display rounding of one decimal per component can accumulate 0.2.
TOLERANCE=.25

def number(x):
    if isinstance(x,bool) or x is None:return None
    try:v=float(x)
    except (TypeError,ValueError,OverflowError):return None
    return v if math.isfinite(v) and v>=0 else None

def audit(predictions):
    groups=defaultdict(dict)
    ignored=Counter()
    for row in predictions:
        try:
            stat=row["stat"]
            if stat not in STATS:continue
            at=datetime.fromisoformat(str(row["captured_at"]).replace("Z","+00:00"))
            tip=datetime.fromisoformat(str(row["start"]).replace("Z","+00:00"))
            if at.tzinfo is None or tip.tzinfo is None or at>=tip:
                ignored["non_pretip_or_invalid_timestamp"]+=1;continue
            forecast=number(row.get("projection"))
            if forecast is None:
                ignored["missing_or_invalid_forecast"]+=1;continue
            key=(str(row["start"]),str(row["game"]),str(row["player_id"]),
                 str(row["team"]),str(row["captured_at"]))
            group=groups[key]
            if stat in group and group[stat]!=forecast:
                group["__conflict__"]=True
            else:group[stat]=forecast
        except (KeyError,TypeError,ValueError):
            ignored["invalid_identity_or_timestamp"]+=1
    checked=[]
    for identity,stats in sorted(groups.items()):
        if stats.get("__conflict__"):
            ignored["conflicting_duplicate_forecasts"]+=1;continue
        if not all(k in stats for k in STATS):
            ignored["incomplete_four_market_group"]+=1;continue
        total=sum(stats[k] for k in ("PTS","REB","AST"))
        gap=round(stats["PRA"]-total,4)
        checked.append({"game":identity[1],"player_id":identity[2],
            "team":identity[3],"captured_at":identity[4],
            "component_sum":round(total,3),"pra_projection":stats["PRA"],
            "pra_minus_components":gap,"consistent":abs(gap)<=TOLERANCE})
    broken=[x for x in checked if not x["consistent"]]
    return {"status":"CROSS_MARKET_COHERENCE_RESEARCH_ONLY",
        "groups_checked":len(checked),"groups_inconsistent":len(broken),
        "inconsistency_rate":round(len(broken)/len(checked),4) if checked else None,
        "tolerance_units":TOLERANCE,"ignored":dict(ignored),
        "largest_discrepancies":sorted(broken,key=lambda x:-abs(x["pra_minus_components"]))[:25],
        "independent_stat_models_may_legitimately_disagree":True,
        "production_forecasts_unchanged":True,
        "settled_hit_rate_improvement_claimed":False}

def main():
    source=json.loads(ARCHIVE.read_text())
    predictions=source.get("predictions",[])
    report=audit(predictions)
    report["generated_at"]=datetime.now(timezone.utc).isoformat()
    report["source"]="immutable_pre_tip_archive"
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print("CROSS MARKET CHECK",report["groups_checked"],"inconsistent",report["groups_inconsistent"])

if __name__=="__main__":main()

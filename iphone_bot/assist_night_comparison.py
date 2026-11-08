"""Independently graded Combined-AI assists by Eastern NBA game date.

One earliest saved pretip sportsbook quote per player/game/market.
Do not aggregate duplicate bookmakers or backdate a later model.
"""
import json
from collections import defaultdict
from datetime import timezone,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .model_performance import independent_rows,forecast_values,finite,utc
except ImportError:
    from model_performance import independent_rows,forecast_values,finite,utc

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"docs/paper_pick_ledger.json"
OUTPUT=ROOT/"docs/assist_nightly_comparison.json"

def compare(records):
    nights=defaultdict(lambda:{"wins":0,"losses":0,"pushes":0,
                              "graded":0,"total_absolute_error":0.})
    for r in independent_rows(records):
        if r.get("market")!="AST":continue
        actual=finite(r.get("actual"));line=finite(r.get("line"))
        pred=forecast_values(r).get("combined")
        if any(x is None for x in (actual,line,pred)):continue
        day=utc(r["event_start"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        a=nights[day]
        a["graded"]+=1
        a["total_absolute_error"]+=abs(actual-pred)
        if actual==line or pred==line:a["pushes"]+=1
        elif (pred>line)==(actual>line):a["wins"]+=1
        else:a["losses"]+=1
    results=[]
    for day,a in sorted(nights.items()):
        n=a["wins"]+a["losses"]
        results.append({"game_date_eastern":day,"wins":a["wins"],
            "losses":a["losses"],"pushes_or_ties":a["pushes"],
            "direction_eligible":n,
            "hit_rate":round(a["wins"]/n,4) if n else None,
            "mae":round(a["total_absolute_error"]/a["graded"],3) if a["graded"] else None})
    first,second=results[:2] if len(results)>=2 else (None,None)
    return {"generated_at":datetime.now(timezone.utc).isoformat(),
        "market":"AST","model":"COMBINED_AI_FROZEN_PREGAME",
        "nightly":results,
        "first_to_second_improvement_percentage_points":round(
            100*(second["hit_rate"]-first["hit_rate"]),2
            ) if first and second and first["hit_rate"] is not None and second["hit_rate"] is not None else None,
        "deduplication":"EARLIEST_PRETIP_PLAYER_EVENT_MARKET_QUOTE",
        "date_timezone":"America/New_York",
        "historical_grades_unchanged":True}

if __name__=="__main__":
    results=compare(json.loads(INPUT.read_text()).get("records",[]))
    OUTPUT.write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(results))

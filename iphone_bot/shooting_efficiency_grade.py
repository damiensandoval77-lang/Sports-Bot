"""Grade only pretip-frozen Shooting V1 shadow against already settled NBA PTS.

Never synthesize historical forecasts at grading time. Each frozen record
remains the original quote; independent evaluation deduplicates per player,
game, stat and central booked threshold, not multiple bookmaker rows.
"""
import json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean
try:
    from .model_performance import independent_rows,forecast_values
except ImportError:
    from model_performance import independent_rows,forecast_values
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"docs/shooting_efficiency_v1_prospective_grades.json"
def real(x):
    if x is None or isinstance(x,bool):return None
    try:
        v=float(x)
        return v if math.isfinite(v) and v>=0 else None
    except (ValueError,TypeError):return None
def grade(records):
    rows=[]
    excluded=defaultdict(int)
    for r in independent_rows(records):
        if r.get("market")!="PTS" or r.get("status")!="SETTLED":continue
        shadow=r.get("shooting_efficiency_v1")
        if not isinstance(shadow,dict) or shadow.get("status")!="PREGAME_SHOOTING_SHADOW_RESEARCH":
            excluded["NO_ORIGINAL_FROZEN_SHADOW"]+=1
            continue
        original=forecast_values(r)["combined"]
        actual=real(r.get("actual"));line=real(r.get("line"))
        candidate=real(shadow.get("blended_projection"))
        raw=real(shadow.get("projection"))
        if None in (original,actual,line,candidate,raw):
            excluded["INCOMPLETE_FROZEN_RECORD"]+=1;continue
        if str(shadow.get("last_prior_game",""))>=str(r["event_start"])[:10]:
            excluded["NON_PRETIP_FEATURE_DATE"]+=1;continue
        rows.append({"game":r.get("game"),"player_id":r.get("player_id"),
            "date":str(r["event_start"])[:10],"actual":actual,
            "line":line,"original":original,"blended":candidate,"raw":raw,
            "opponent_adjusted":shadow.get("opponent_adjustment_applied") is True})
    def stats(name):
        if not rows:return {"graded":0,"mae":None,"directional_wins":0,
                            "directional_losses":0,"hit_rate":None}
        eligible=[r for r in rows if r["actual"]!=r["line"] and r[name]!=r["line"]]
        wins=sum((r[name]>r["line"])==(r["actual"]>r["line"]) for r in eligible)
        return {"graded":len(eligible),"mae":round(mean(abs(r[name]-r["actual"]) for r in rows),4),
                "directional_wins":wins,"directional_losses":len(eligible)-wins,
                "hit_rate":round(wins/len(eligible),4) if eligible else None}
    return {"status":"FROZEN_SHOOTING_V1_PROSPECTIVE_GRADING_ONLY",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "independent_frozen_pts_markets":len(rows),
        "distinct_game_dates":len({r["date"] for r in rows}),
        "combined_ai":stats("original"),"shooting_v1_raw":stats("raw"),
        "shooting_v1_blend":stats("blended"),
        "skipped":dict(excluded),"production_model_changed":False,
        "verified_edge":False,
        "notice":"Original saved pretip shooting V1 projection graded without recomputation, and only on identical eligible settled points markets. Empty until new eligible captures settle."}
def main():
    report=grade(json.loads(SOURCE.read_text()).get("records",[]))
    OUT.write_text(json.dumps(report,indent=2)+"\n")
    print("FROZEN SHOOTING V1 GRADING:",json.dumps({k:report[k] for k in
          ("independent_frozen_pts_markets","distinct_game_dates","skipped","combined_ai","shooting_v1_blend")}))
if __name__=="__main__":main()

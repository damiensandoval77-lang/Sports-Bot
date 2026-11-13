"""Publish independently modeled shadow chances read-only, never betting grades.

Preserve newer research if older CI completes later. Any invalid/incomplete
source must not blank a good feed or masquerade as a calibrated HIT EST.
"""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from math import isfinite

EXPECTED="POSITION_MATCHUP_RESEARCH_ONLY_PROBABILITY"
METHOD="POSITION_V_POSITION_DEF_RATING_RESEARCH_ANALYTIC_V1"

def stamp(value):
    if not isinstance(value,str):raise ValueError("timestamp absent")
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone missing")
    return t.astimezone(timezone.utc)

def validate(feed):
    if feed.get("status")!=EXPECTED or feed.get("calibrated") is not False or feed.get("production_approved") is not False or feed.get("published_to_cards") is not False:
        raise ValueError("not a guarded uncalibrated research feed")
    at=stamp(feed["captured_at"])
    records=feed.get("records")
    if not isinstance(records,list) or len(records)<1 or len(records)>5000:
        raise ValueError("no eligible original market quotes")
    seen=set()
    for row in records:
        if not isinstance(row,dict):raise ValueError("invalid market record")
        freeze=stamp(row["captured_at"])
        start=stamp(row["start"])
        if not freeze<start or at<freeze:
            raise ValueError("not a frozen market before game start")
        if row.get("stat") not in ("PTS","REB","AST","PRA") or row.get("original_side") not in ("MORE","LESS") or not row.get("player_id") or not row.get("team") or not row.get("opponent"):
            raise ValueError("incomplete market identity")
        if type(row.get("line")) not in (int,float) or not isfinite(row["line"]) or row["line"]<0:
            raise ValueError("invalid standard line")
        chance=row.get("estimated_hit_chance") or {}
        if (chance.get("method")!=METHOD or chance.get("calibrated") is not False or
            chance.get("research_only") is not True or
            chance.get("verified_betting_edge") is not False or
            chance.get("opponent_aware_inputs_sourced") is not True or
            chance.get("opponent_adjustment_validated") is not False):
            raise ValueError("chance provenance not sufficient")
        value=chance.get("modeled_selected_probability")
        if type(value) not in (int,float) or not isfinite(value) or not 0<=value<=1:
            raise ValueError("invalid model probability")
        key=tuple(str(row.get(x)) for x in
             ("player_id","team","opponent","stat","start","line","captured_at"))
        if key in seen:raise ValueError("ambiguous duplicate standard quote")
        seen.add(key)
    if feed.get("eligible_opponent_conditioned_estimates")!=len(records):
        raise ValueError("model coverage mismatch")
    return at

def choose(incoming,existing=None):
    next_time=validate(incoming)
    if existing:
        try:
            prior_time=validate(existing)
        except (KeyError,TypeError,ValueError):
            prior_time=None
        if prior_time is not None and prior_time>=next_time:
            return existing,False
    # Privacy-safe projection only, no extras, same research-only metadata.
    feed={**incoming,"published_to_cards":False,"production_approved":False,
          "presentation_policy":"EXPERIMENTAL_MATCHUP_PREVIEW_NOT_CERTIFIED_HIT_EST"}
    return feed,True

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--incoming",required=True)
    ap.add_argument("--current",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    new=json.loads(Path(args.incoming).read_text())
    path=Path(args.current)
    old=json.loads(path.read_text()) if path.exists() else None
    chosen,changed=choose(new,old)
    Path(args.output).write_text(json.dumps(chosen,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":chosen["status"],"count":len(chosen["records"]),
                      "updated":changed,"captured_at":chosen["captured_at"],
                      "production_approved":False}))
if __name__=="__main__":main()

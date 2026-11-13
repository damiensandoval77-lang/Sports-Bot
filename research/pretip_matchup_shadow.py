"""Shadow-only position matchup probability against authentic standard lines.

The *center* of each outcome distribution is adjusted for the specific opponent
position, opponent defensive rating and pregame minutes. Residual errors come
from the *older-season model's independent validation*, not past betting hits.
No random simulation, no historical exact-line win frequency. Until accuracy
is prospectively calibrated these numbers are withheld from production cards.
"""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from math import isfinite
import numpy as np
from research.freeze_position_rating_quote_join import assemble as join_quotes
from research.position_rating_hit_candidate import time

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/"models/nba/research/lagged_matchup_all_markets.joblib"
METHOD="POSITION_V_POSITION_DEF_RATING_RESEARCH_ANALYTIC_V1"
IDX={"PTS":0,"REB":1,"AST":2}

def analyze(snapshot,joins,residual_matrix,*,captured_at,model_id):
    residuals=np.asarray(residual_matrix,dtype=float)
    if residuals.ndim!=2 or residuals.shape[1]!=3 or residuals.shape[0]<1000:
        raise ValueError("independent PTS/REB/AST residual reference unavailable")
    if not np.isfinite(residuals).all():
        raise ValueError("nonfinite validation errors")
    if not model_id:
        raise ValueError("model provenance missing")
    quoted={}
    for p in snapshot.get("predictions",[]):
        key=(str(p.get("player_id")),p.get("team"),p.get("opponent"),
             p.get("stat"),float(p.get("line") or 0),p.get("captured_at"))
        if key in quoted:raise ValueError("ambiguous frozen original quote identity")
        quoted[key]=p
    result=[]
    for x in joins.get("results",[]):
        key=(x["player_id"],x["team"],x["opponent"],x["stat"],
             float(x["original_line"]),x["pick_captured_at"])
        quoted_item=quoted.get(key)
        if not quoted_item:
            raise ValueError("no exact frozen standard quote for research matchup")
        if time(x["pick_captured_at"])>=time(x["start"]):
            raise ValueError("posttip model input")
        if time(joins["captured_at"])>time(captured_at):
            raise ValueError("research join published in future")
        stat=x["stat"]
        errors=(residuals[:,IDX[stat]] if stat!="PRA"
                else np.sum(residuals,axis=1))
        projection=float(x["experimental_matchup_projection"])
        line=float(x["original_line"])
        if not isfinite(projection) or projection<=0 or not isfinite(line):
            raise ValueError("invalid fixed line or matchup projection")
        values=np.maximum(0.,errors+projection)
        chance_more=float(np.mean(values>line))
        chance_less=float(np.mean(values<line))
        chance_push=float(np.mean(values==line))
        # The original side is frozen; never manufacture a new PrizePicks
        # quote from the model's revised matchup projection.
        original=quoted_item.get("estimated_hit_chance") or {}
        selected=str(original.get("modeled_direction") or "").upper()
        if selected not in ("MORE","LESS"):
            raise ValueError("invalid frozen direction")
        modeled=chance_more if selected=="MORE" else chance_less
        result.append({
            "player_id":x["player_id"],"player":x.get("player"),
            "team":x["team"],"opponent":x["opponent"],"stat":stat,
            "listed_position":x["position"],"start":x["start"],
            "line":line,"original_projection":x["original_projection"],
            "matchup_projection":projection,
            "captured_at":x["pick_captured_at"],"original_side":selected,
            "estimated_hit_chance":{
                "method":METHOD,"model_id":model_id,
                "modeled_selected_probability":round(modeled,4),
                "modeled_more_probability":round(chance_more,4),
                "modeled_less_probability":round(chance_less,4),
                "modeled_push_probability":round(chance_push,4),
                "reference_validation_games":len(values),
                "source_provenance":x["source_provenance"],
                "calibrated":False,"research_only":True,
                "opponent_aware_inputs_sourced":True,
                "opponent_adjustment_validated":False,
                "verified_betting_edge":False,
                "note":"Opponent-centered analytical error distribution, not simulation or past line-hit frequency; not calibrated for 2026-27."}})
    return {
        "status":"POSITION_MATCHUP_RESEARCH_ONLY_PROBABILITY",
        "captured_at":captured_at,"model_id":model_id,
        "input_market_quotes":joins["input_quotes"],
        "eligible_opponent_conditioned_estimates":len(result),
        "source_exclusions":joins["exclusions"],
        "records":result,"published_to_cards":False,
        "replaced_frozen_picks":False,"changed_grades":False,
        "production_approved":False,
        "calibrated":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--quotes",default="docs/lagged_matchup_live_all_markets.json")
    p.add_argument("--joined",default="position-rating-quote-research.json")
    p.add_argument("--pack",default=str(PACK))
    p.add_argument("--output",default="matchup-shadow-estimates-research.json")
    a=p.parse_args()
    import joblib
    pack=joblib.load(a.pack)
    if pack.get("calibrated") is not False or pack.get("research_only") is not True:
        raise ValueError("unexpected residual model provenance")
    data=analyze(json.loads(Path(a.quotes).read_text()),
        json.loads(Path(a.joined).read_text()),
        pack["validation_residual_triplets"],
        captured_at=datetime.now(timezone.utc).isoformat(),
        model_id="NBA_2022_24_PVP_DEF_RATING_RESEARCH")
    Path(a.output).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:data[k] for k in ("status","input_market_quotes",
        "eligible_opponent_conditioned_estimates","source_exclusions",
        "published_to_cards","calibrated")},indent=2))
if __name__=="__main__":main()

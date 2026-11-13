"""Frozen research-only disagreement diagnostics across explicitly available forecasts.

Combined is derived from originals and is NOT an independent voter. Missing
opponent or sanity shadow must not be silently replaced by Combined.
No probabilities, prices, or production picks are modified.
"""
from collections import Counter,defaultdict

MARKETS={"PTS":3.0,"REB":1.5,"AST":1.5,"PRA":5.0}
METHOD="PREGAME_MODEL_DISAGREEMENT_RESEARCH_V1_FIXED_MARKET_THRESHOLDS"

def valid(x):
    if x is None or isinstance(x,bool):return None
    try:
        n=float(x)
        import math
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError,OverflowError):return None

def direction(value,line):
    if value is None:return "MISSING"
    if value==line:return "AT_LINE"
    return "OVER" if value>line else "UNDER"

def detect(*,market,line,original,opponent,combined,sanity=None,
           opponent_verified=False,sanity_status=None):
    threshold=MARKETS.get(market)
    q=valid(line)
    projections={"original":valid(original),
                 "opponent_aware":valid(opponent) if opponent_verified else None,
                 "combined":valid(combined),
                 "sanity_shadow":valid(sanity) if sanity_status in
                      ("SHADOW_CANDIDATE_UNVALIDATED","NO_LARGE_DEVIATION") else None}
    result={"method":METHOD,"status":"INSUFFICIENT_MODEL_COMPARISON",
            "threshold_absolute":threshold,"projections":projections,
            "directions":{},"flags":[],"opponent_verified":bool(opponent_verified),
            "sanity_status":sanity_status,
            "independent_models_available":0,
            "spread_absolute":None,"spread_fraction_of_combined":None,
            "research_only":True,"prediction_changed":False,
            "probability_changed":False,"pick_changed":False,
            "confidence_verified":False}
    if threshold is None or q is None or projections["combined"] is None:
        return {**result,"status":"INVALID_OR_UNSUPPORTED_INPUT"}
    directions={name:direction(v,q) for name,v in projections.items()}
    result["directions"]=directions
    independent=[projections[k] for k in ("original","opponent_aware") if projections[k] is not None]
    result["independent_models_available"]=len(independent)
    flags=[]
    if projections["opponent_aware"] is None:flags.append("OPPONENT_MODEL_UNAVAILABLE")
    if projections["sanity_shadow"] is None:flags.append("SANITY_SHADOW_UNAVAILABLE")
    if len(independent)<2:
        return {**result,"status":"PARTIAL_MODEL_COVERAGE",
                "flags":flags}
    spread=abs(independent[0]-independent[1])
    result["spread_absolute"]=round(spread,3)
    result["spread_fraction_of_combined"]=round(
        spread/max(projections["combined"],1),4)
    if spread>=threshold:flags.append("MATERIAL_ORIGINAL_OPPONENT_SPREAD")
    if directions["original"]!=directions["opponent_aware"]:
        flags.append("ORIGINAL_OPPONENT_DIRECTION_CONFLICT")
    if projections["sanity_shadow"] is not None:
        if directions["sanity_shadow"]!=directions["combined"]:
            flags.append("SANITY_COMBINED_DIRECTION_CONFLICT")
        if abs(projections["sanity_shadow"]-projections["combined"])>=threshold:
            flags.append("MATERIAL_SANITY_COMBINED_SPREAD")
    # "Agreement" cannot be granted when the independent models disagree.
    result["flags"]=flags
    result["status"]="MODEL_DISAGREEMENT_REVIEW" if any(x in flags for x in (
        "MATERIAL_ORIGINAL_OPPONENT_SPREAD",
        "ORIGINAL_OPPONENT_DIRECTION_CONFLICT",
        "SANITY_COMBINED_DIRECTION_CONFLICT",
        "MATERIAL_SANITY_COMBINED_SPREAD")) else (
        "TWO_MODEL_AGREEMENT_SHADOW_MISSING" if projections["sanity_shadow"] is None
        else "RESEARCH_MODEL_AGREEMENT")
    return result

def report(ledger,paper_rows,independent_rows,utc):
    """Compare flagged vs unflagged *frozen* Combined forecasts, no tuning."""
    final={}
    for r in independent_rows(paper_rows):
        if r.get("status")!="SETTLED":continue
        try:
            key=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["market"])
            final[key]=float(r["actual"])
        except (KeyError,TypeError,ValueError):continue
    seen=set()
    coverage=Counter()
    flags=Counter()
    segments=defaultdict(list)
    pending=Counter()
    for row in sorted(ledger,key=lambda r:str(r.get("captured_at",""))):
        d=row.get("model_disagreement_v1")
        if not isinstance(d,dict):continue
        try:
            when=utc(row["event_start"])
            if utc(row["captured_at"])>=when:continue
            key=(when.isoformat(),str(row["player_id"]),row["market"])
            if key in seen:continue
            seen.add(key)
            state=str(d.get("status","UNKNOWN"))
            coverage[state]+=1
            for flag in d.get("flags",[]):flags[str(flag)]+=1
            if key not in final:
                pending[state]+=1
                continue
            combined=valid(row.get("combined_projection"))
            if combined is None:continue
            tagged=state=="MODEL_DISAGREEMENT_REVIEW"
            segments["flagged" if tagged else "not_flagged"].append(
                (abs(combined-final[key]),when.date().isoformat()))
        except (TypeError,KeyError,ValueError):continue
    def metrics(items):
        return {"paired_markets":len(items),
                "distinct_utc_game_dates":len({d for _,d in items}),
                "combined_mae":round(sum(x for x,_ in items)/len(items),4)
                    if items else None}
    return {"status":"UNVALIDATED_MODEL_DISAGREEMENT_RESEARCH",
            "captured_by_status":dict(coverage),
            "flag_counts":dict(flags),"pending_by_status":dict(pending),
            "flagged_settled":metrics(segments["flagged"]),
            "unflagged_settled":metrics(segments["not_flagged"]),
            "research_only":True,"live_picks_changed":False,
            "live_probabilities_changed":False,
            "model_improvement_established":False}

"""Pre-registered prospective research screener, NOT a production recommendation.

Only applied at initial pretip paper snapshot. A fixed and conservative
agreement/margin gate; no parameters estimated from completed games.
"""
from collections import defaultdict
from math import isfinite

RULE="RESEARCH_SELECTIVE_V1_FIXED_2026_11_07"
MIN_MARGIN={"PTS":3.0,"REB":1.5,"AST":1.5,"PRA":4.0}

def _number(x):
    try:
        n=float(x)
        return n if isfinite(n) and n>=0 else None
    except (TypeError,ValueError,OverflowError):
        return None

def screen(market,line,original,opponent,combined):
    """Freeze PASS/CONSIDER from pretip numbers; never use the actual."""
    margin=MIN_MARGIN.get(market)
    numbers=tuple(_number(x) for x in (line,original,opponent,combined))
    base={"rule":RULE,"decision":"PASS","side":None,"reason":None,
          "research_only":True,"no_live_pick_change":True}
    if margin is None or any(x is None for x in numbers):
        return {**base,"reason":"MISSING_MODEL_OR_MARKET"}
    quoted,a,b,c=numbers
    if min(abs(a-quoted),abs(b-quoted),abs(c-quoted))==0:
        return {**base,"reason":"TIE_TO_MARKET"}
    sides=(a>quoted,b>quoted,c>quoted)
    if len(set(sides))!=1:
        return {**base,"reason":"MODELS_DISAGREE"}
    if abs(c-quoted)<margin:
        return {**base,"reason":"INSUFFICIENT_PROJECTION_MARGIN"}
    return {**base,"decision":"CONSIDER","side":"OVER" if c>quoted else "UNDER",
            "reason":"FIXED_MARGIN_AND_MODEL_AGREEMENT"}

def evaluate(records):
    """Descriptive, deduped grading of decisions already frozen pretip.

    Unscreened historical picks are NEVER retroactively classified.
    """
    chosen={}
    decisions=defaultdict(lambda:{"n":0,"wins":0,"losses":0,"pushes":0,
                                  "paper_profit_units":0.0,"priced":0})
    for r in sorted(records,key=lambda x:x.get("captured_at","")):
        snap=r.get("research_selective_v1")
        if not isinstance(snap,dict) or snap.get("rule")!=RULE:continue
        key=(r.get("event_start"),r.get("player_id"),r.get("team"),r.get("market"))
        chosen.setdefault(key,r)
    pending=0
    for r in chosen.values():
        snap=r["research_selective_v1"]
        if snap.get("decision")!="CONSIDER":continue
        if r.get("status")!="SETTLED":
            pending+=1
            continue
        line=_number(r.get("line"));actual=_number(r.get("actual"))
        if line is None or actual is None:continue
        stat=str(r["market"])
        d=decisions[stat]
        d["n"]+=1
        if line==actual:d["pushes"]+=1
        elif (actual>line)==(snap["side"]=="OVER"):d["wins"]+=1
        else:d["losses"]+=1
        odds=r.get("over_odds") if snap["side"]=="OVER" else r.get("under_odds")
        try:
            from .paper_pick_pipeline import payout
            unit=payout(odds)
        except (ImportError,ValueError,TypeError,OverflowError):
            try:
                from paper_pick_pipeline import payout
                unit=payout(odds)
            except (ImportError,ValueError,TypeError,OverflowError):
                continue
        d["priced"]+=1
        if actual!=line:
            d["paper_profit_units"]+=(unit if (actual>line)==(snap["side"]=="OVER") else -1.0)
    markets={}
    for m in MIN_MARGIN:
        d=dict(decisions[m])
        n=d["wins"]+d["losses"]
        d["hit_rate"]=round(d["wins"]/n,4) if n else None
        d["paper_roi"]=round(d["paper_profit_units"]/d["priced"],4) if d["priced"] else None
        d["paper_profit_units"]=round(d["paper_profit_units"],4)
        markets[m]=d
    return {"rule":RULE,"status":"PROSPECTIVE_FIXED_RULE_RESEARCH_ONLY",
            "locked_markets":len(chosen),
            "considered_markets":sum(r["research_selective_v1"]["decision"]=="CONSIDER" for r in chosen.values()),
            "pending_considered":pending,"by_stat":markets,
            "historical_unscreened_excluded":True,"live_model_unchanged":True}

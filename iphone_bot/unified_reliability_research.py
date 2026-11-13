"""Single descriptive research reliability view of immutable pregame research data.

No numeric trust score, win chance, betting recommendation or postgame retrofit.
Only the earliest pre-tip capture of each player/event/market appears; old ledger
rows without a tool's frozen output are explicitly marked missing.
"""
from collections import Counter
from datetime import datetime,timezone

try:
    from .paper_pick_pipeline import utc
    from .confidence_readiness_audit import valid_pregame_proxy
except ImportError:
    from paper_pick_pipeline import utc
    from confidence_readiness_audit import valid_pregame_proxy

MODEL_KEYS=("sanity_shadow_v1","stress_test_20k_v1","model_disagreement_v1")
METHOD="PREGAME_UNIFIED_RESEARCH_FLAGS_V1"
MAX_PREVIEW=60

def observation_key(row):
    return (utc(row["event_start"]).isoformat(),str(row["player_id"]),
            str(row["team"]),str(row["market"]))

def view(records,quotes,*,generated_at=None):
    if generated_at is None:
        generated_at=datetime.now(timezone.utc).isoformat()
    captured={}
    rejected=Counter()
    for row in sorted(records,key=lambda r:str(r.get("captured_at",""))):
        try:
            if utc(row["captured_at"])>=utc(row["event_start"]):
                rejected["late_or_not_pregame"]+=1
                continue
            key=observation_key(row)
            if key in captured:
                rejected["duplicate_capture"]+=1
                continue
            captured[key]=row
        except (KeyError,TypeError,ValueError):
            rejected["invalid_record_identity"]+=1
    buckets=Counter()
    warnings=Counter()
    availability=Counter()
    details=[]
    for key,row in captured.items():
        sanity=row.get("sanity_shadow_v1")
        stress=row.get("stress_test_20k_v1")
        models=row.get("model_disagreement_v1")
        reason=[]
        for name,object_ in zip(MODEL_KEYS,(sanity,stress,models)):
            if not isinstance(object_,dict):
                availability[name+"_missing"]+=1
                reason.append("MISSING_FROZEN_"+name.upper())
            else:
                availability[name+"_present"]+=1
        if isinstance(sanity,dict):
            reason.extend("SANITY_"+str(w) for w in sanity.get("warnings",[]) if isinstance(w,str))
            if sanity.get("status")=="REVIEW_ONLY_UNCERTAIN_INPUTS":
                reason.append("SANITY_ADJUSTMENT_WITHHELD")
        if isinstance(stress,dict):
            reason.extend("STRESS_"+str(w) for w in stress.get("warnings",[]) if isinstance(w,str))
            if stress.get("fragile_high_confidence") is True:
                reason.append("STRESS_FRAGILE_HIGH_SIMULATED_CONFIDENCE")
            if stress.get("status")!="CONDITIONAL_STRESS_RESEARCH_ONLY":
                reason.append("STRESS_INSUFFICIENT_VALID_INPUTS")
        if isinstance(models,dict):
            reason.extend("MODELS_"+str(w) for w in models.get("flags",[]) if isinstance(w,str))
            if models.get("status")=="MODEL_DISAGREEMENT_REVIEW":
                reason.append("MODELS_REVIEW_REQUIRED")
            elif models.get("status")!="RESEARCH_MODEL_AGREEMENT":
                reason.append("MODELS_INCOMPLETE_OR_NOT_FULLY_SUPPORTED")
        reason=sorted(set(reason))
        # Unknown inputs stay unknown; a clean research screen never means
        # a verified high-confidence market.
        missing=any(not isinstance(row.get(k),dict) for k in MODEL_KEYS)
        warning=any(r.startswith(("SANITY_LARGE_SEASON","SANITY_EXPECTED_MINUTES_DISAGREE",
            "SANITY_HIGH_RECENT","SANITY_STALE","SANITY_ADJUSTMENT_WITHHELD",
            "STRESS_FRAGILE","STRESS_HIGH_MINUTES","STRESS_MINUTES_DISAGREE",
            "MODELS_ORIGINAL_OPPONENT_DIRECTION","MODELS_MATERIAL_",
            "MODELS_SANITY_COMBINED_DIRECTION","MODELS_REVIEW_REQUIRED"))
            for r in reason)
        classification=("NEEDS_REVIEW" if warning else
                        "INSUFFICIENT_RESEARCH_COVERAGE" if missing or reason else
                        "NO_RESEARCH_FLAGS_UNVALIDATED")
        buckets[classification]+=1
        for r in reason:warnings[r]+=1
        details.append({"event_start":key[0],"player_id":key[1],
                        "team":key[2],"market":key[3],
                        "player":str(row.get("player","")),
                        "combined_projection":row.get("combined_projection"),
                        "classification":classification,
                        "reasons":reason,
                        "data_available":{k:isinstance(row.get(k),dict) for k in MODEL_KEYS}})
    # Confidence is quote-level metadata, not independent player observations.
    # No after-game probability backfill is allowed.
    valid_proxy=sum(1 for q in quotes if valid_pregame_proxy(q))
    graded_proxy=sum(1 for q in quotes if q.get("status")=="SETTLED"
                     and valid_pregame_proxy(q))
    return {"method":METHOD,"status":"DESCRIPTIVE_PREGAME_RELIABILITY_RESEARCH_ONLY",
        "generated_at":generated_at,
        "independent_research_markets":len(captured),
        "classification_counts":dict(buckets),
        "data_availability":dict(availability),
        "reasons_by_code":dict(warnings),
        "excluded_records":dict(rejected),
        "recent_markets":sorted(details,key=lambda r:(
            r["event_start"],r["player_id"],r["market"]),reverse=True)[:MAX_PREVIEW],
        "confidence_proxy_quote_coverage":{
            "valid_pregame_quote_snapshots":valid_proxy,
            "settled_quote_snapshots_with_frozen_proxy":graded_proxy,
            "unit":"bookmaker_quote_snapshots_not_independent_market_outcomes",
            "confidence_calibrated":False},
        "unverified_clean_does_not_mean_safe":True,
        "no_bet_recommendations":True,
        "no_live_picks_changed":True,
        "no_live_probabilities_changed":True,
        "no_accuracy_improvement_claimed":True}

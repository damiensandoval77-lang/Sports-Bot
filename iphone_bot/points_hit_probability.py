"""Player/line-specific experimental point-over probabilities, 20k seeded draws.

Uses residuals from a distinct 2024-25 season, never from training games,
current target game, betting lines or current player outcomes. A broad
projection bucket controls residual scale; 15% global shrink reduces spurious
bucket certainty. Not a calibrated PrizePicks hit rate or proven edge.
"""
import hashlib
import math
import numpy as np

METHOD="2024_25_OUT_OF_TRAINING_RESIDUAL_20K_BOOTSTRAP_UNVALIDATED"
DRAWS=20000
MIN_GLOBAL=1000
MIN_BUCKET=300
BUCKET_EDGES=(10.0,20.0,30.0)

def bucket(prediction):
    p=float(prediction)
    if not math.isfinite(p) or p<0 or p>100:
        raise ValueError("Bad projected points")
    return str(int(np.searchsorted(BUCKET_EDGES,p,side="right")))

def make_reference(projections,actuals):
    p=np.asarray(projections,dtype=float)
    a=np.asarray(actuals,dtype=float)
    if len(p)!=len(a) or len(p)<MIN_GLOBAL:
        raise ValueError("Insufficient independent validation observations")
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(a)) or np.any(p<0) or np.any(a<0):
        raise ValueError("Invalid validation results")
    residuals=a-p
    bins={}
    for i in range(4):
        mask=(np.searchsorted(BUCKET_EDGES,p,side="right")==i)
        if int(mask.sum())>=MIN_BUCKET:
            bins[str(i)]=[round(float(v),6) for v in residuals[mask]]
    if len(bins)<3:raise ValueError("Too few projection-range calibration samples")
    return {"status":"HISTORICAL_PROBABILITY_REFERENCE_ONLY",
       "source":"2024-25_OUT_OF_TRAINING_POINTS_RESIDUALS",
       "residuals":[round(float(v),6) for v in residuals],
       "by_projection_bucket":bins,"sample_size":len(residuals),
       "training_target_season_excluded":True,
       "calibrated_for_prizepicks":False}

def estimate(prediction,line,reference,identity,draws=DRAWS):
    p=float(prediction);q=float(line)
    if not math.isfinite(p) or not math.isfinite(q) or not 0<=p<=100 or not 0<=q<=100:
        raise ValueError("Bad projection or actual line")
    if draws!=DRAWS:raise ValueError("Exactly 20,000 draws required")
    if reference.get("status")!="HISTORICAL_PROBABILITY_REFERENCE_ONLY" or reference.get("source")!="2024-25_OUT_OF_TRAINING_POINTS_RESIDUALS" or reference.get("training_target_season_excluded") is not True:
        raise ValueError("Invalid historical probability reference")
    errors=np.asarray(reference.get("residuals",[]),dtype=float)
    if len(errors)<MIN_GLOBAL or len(errors)!=reference.get("sample_size") or not np.all(np.isfinite(errors)):
        raise ValueError("Invalid complete calibration errors")
    group=np.asarray(reference.get("by_projection_bucket",{}).get(bucket(p),[]),dtype=float)
    if len(group)<MIN_BUCKET or not np.all(np.isfinite(group)):
        group=errors;group_used="GLOBAL_FALLBACK"
    else:group_used="SIMILAR_PROJECTED_POINTS"
    seed=int.from_bytes(hashlib.sha256(str(identity).encode("utf-8")).digest()[:8],"big")
    rng=np.random.default_rng(seed)
    # Fixed 85% similar-scoring and 15% all-player mix, to prevent unjustified
    # apparent certainty from small scoring ranges.
    n_local=int(draws*.85)
    sampled=np.concatenate((rng.choice(group,size=n_local,replace=True),
                            rng.choice(errors,size=draws-n_local,replace=True)))
    # NBA points are integer totals; restore discrete support and push cases.
    scored=np.maximum(0,np.rint(p+sampled))
    above=int(np.count_nonzero(scored>q))
    below=int(np.count_nonzero(scored<q))
    pushes=draws-above-below
    over=above/draws
    under=below/draws
    side="More" if over>under else "Less" if under>over else "No lean"
    selected=max(over,under) if side!="No lean" else None
    return {"method":METHOD,"draws":draws,
       "estimated_over_probability":round(over,4),
       "estimated_under_probability":round(under,4),
       "estimated_push_probability":round(pushes/draws,4),
       "estimated_selected_side":side,
       "estimated_selected_probability":round(selected,4) if selected is not None else None,
       "validation_residual_count":len(errors),
       "similar_range_residual_count":len(group),
       "conditioning":group_used,
       "calibrated":False,"betting_edge_verified":False,
       "modeling_note":"Hypothetical chance from historical error distributions; live hit-rate accuracy not yet verified."}

"""Twenty thousand CORRELATED joint scoring scenarios per exact market line.

A single historical player-game row contributes PTS/REB/AST errors together,
not three independent draws; simulated PRA is the sum of those components.
Source is the 2024-25 validation season excluded from fitting. Not calibrated
against authentic PrizePicks outcomes or evidence of a profitable wager.
"""
import hashlib
import math
import numpy as np

DRAWS=20000
METHOD="JOINT_2024_25_VALIDATION_RESIDUALS_20K_UNCALIBRATED"

def simulate(projections,line,market,residual_triplets,identity,draws=DRAWS):
    if draws!=DRAWS:raise ValueError("Only approved 20k research simulation")
    if market not in ("PTS","REB","AST","PRA"):raise ValueError("Unsupported market")
    p=np.asarray([projections[k] for k in ("PTS","REB","AST")],dtype=float)
    r=np.asarray(residual_triplets,dtype=float)
    try:threshold=float(line)
    except (ValueError,TypeError):raise ValueError("Invalid line")
    if p.shape!=(3,) or not np.all(np.isfinite(p)) or np.any(p<0) or np.any(p>100):
        raise ValueError("Incomplete component projections")
    if r.ndim!=2 or r.shape[1]!=3 or len(r)<1000 or not np.isfinite(r).all():
        raise ValueError("Missing matched historical residual triplets")
    if not math.isfinite(threshold) or not 0<=threshold<=200:
        raise ValueError("Invalid authentic comparison threshold")
    seed=int.from_bytes(hashlib.sha256(str(identity).encode("utf-8")).digest()[:8],"big")
    rng=np.random.default_rng(seed)
    draws_index=rng.integers(len(r),size=draws)
    components=np.maximum(0,np.rint(p+r[draws_index]))
    idx={"PTS":0,"REB":1,"AST":2}
    outcome=components[:,idx[market]] if market in idx else components.sum(axis=1)
    over=int(np.count_nonzero(outcome>threshold))
    under=int(np.count_nonzero(outcome<threshold))
    push=draws-over-under
    direction="More" if over>under else "Less" if under>over else "No lean"
    probability=max(over,under)/draws if direction!="No lean" else None
    projected=float(p.sum()) if market=="PRA" else float(p[idx[market]])
    return {"method":METHOD,"draws":draws,"market":market,
       "projection":round(projected,3),
       "modeled_more_probability":round(over/draws,4),
       "modeled_less_probability":round(under/draws,4),
       "modeled_push_probability":round(push/draws,4),
       "modeled_direction":direction,
       "modeled_selected_probability":round(probability,4) if probability is not None else None,
       "reference_player_games":len(r),
       "component_projections":{"PTS":round(float(p[0]),3),
           "REB":round(float(p[1]),3),"AST":round(float(p[2]),3)},
       "PRA_joint_distribution":market=="PRA",
       "calibrated":False,"verified_betting_edge":False,
       "note":"Historical residual-based estimate only; not a verified live hit percentage."}

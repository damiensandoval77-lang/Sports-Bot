"""Compact, strictly factual explanations for experimental NBA prop projections.

Explanations describe observed historical inputs and the ensemble arithmetic.
They do not attribute causal feature importance to an opaque regression model.
Opponent total allowances are team-wide, not direct positional matchup evidence.
"""
import math

STAT_NAMES={"PTS":"points","REB":"rebounds","AST":"assists","PRA":"points + rebounds + assists"}

def _number(value):
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (ValueError,TypeError):
        return None

def explain_projection(stat,line,original,shadow,combined,form,
                       minutes=None,defense=None):
    """Generate at most three concise sentences from verified pregame data."""
    if stat not in STAT_NAMES:
        raise ValueError("Unsupported NBA market")
    market=STAT_NAMES[stat]
    previous=_number(form.get(stat+"_L5"))
    longer=_number(form.get(stat+"_L10"))
    if stat=="PRA":
        if previous is None:
            vals=[_number(form.get(x+"_L5")) for x in ("PTS","REB","AST")]
            if all(v is not None for v in vals): previous=sum(vals)
        if longer is None:
            vals=[_number(form.get(x+"_L10")) for x in ("PTS","REB","AST")]
            if all(v is not None for v in vals): longer=sum(vals)
    parts=[]
    if previous is not None and longer is not None:
        parts.append(f"Recent form: {previous:.1f} {market} per game over the last 5, versus {longer:.1f} over up to the last 10 games.")
    elif previous is not None:
        parts.append(f"Recent form: {previous:.1f} {market} per game over the last 5.")
    if isinstance(minutes,dict):
        m=_number(minutes.get("observed_l5"))
        if m is not None:
            phrase=f"Minutes averaged {m:.1f} over the last 5 games"
            if minutes.get("review_needed") is True:phrase+=" and have varied"
            parts.append(phrase+".")
    sh=_number(shadow)
    base=_number(original)
    blend=_number(combined)
    if sh is not None and base is not None and blend is not None:
        parts.append(f"The opponent-aware model estimates {sh:.1f} versus the original model's {base:.1f}; their midpoint is {blend:.1f}.")
    else:
        parts.append("Opponent-aware projection unavailable; the original model is used without a matchup adjustment.")
    # Keep the short summary focused; opponent totals may be offered separately
    # as descriptive context but do not prove why the model moved.
    return {"sentences":parts[:3],
            "status":"DESCRIPTIVE_FACTS_NOT_CAUSAL_EXPLANATION",
            "injury_verified":False,
            "defender_assignment_verified":False}

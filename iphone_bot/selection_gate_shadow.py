"""Prospective-only abstention gate for frozen NBA Combined AI decisions.

No market selection is promoted to a real wager. Fixed input-quality and
stability rules; not thresholds fitted from the Nov 6 settled results.
The reason codes let future paper tests evaluate abstention against ALL
same-slate picks, including the picks the gate skipped.
"""
from statistics import pstdev,mean
import math

MIN_PRIOR_GAMES=8
MINUTES_VOLATILITY_LIMIT=6.0
MINUTES_TREND_LIMIT=5.0

def finite(value):
    if value is None or isinstance(value,bool):return None
    try:
        x=float(value)
        return x if math.isfinite(x) and x>=0 else None
    except (TypeError,ValueError):return None

def pregame_gate(stat,line,combined,original,opponent,historical,opportunity,
                 injury_status):
    reasons=[]
    if stat not in ("PTS","REB","AST","PRA"):
        reasons.append("UNSUPPORTED_MARKET")
    if any(finite(x) is None for x in (line,combined,original,opponent)):
        reasons.append("MISSING_FROZEN_FORECAST_OR_LINE")
    elif combined==line:
        reasons.append("NO_DIRECTION")
    elif ((float(original)-float(line))*(float(opponent)-float(line))<=0):
        reasons.append("ORIGINAL_AND_OPPONENT_MODELS_DISAGREE_ON_SIDE")
    # This gate deliberately does not use high simulated hit% as confidence.
    if len(historical)<MIN_PRIOR_GAMES:
        reasons.append("INSUFFICIENT_PREGAME_PLAYER_HISTORY")
    else:
        minutes=[finite(r.get("MIN")) for r in historical[-5:]]
        if any(m is None or m==0 for m in minutes):
            reasons.append("INVALID_RECENT_MINUTES")
        else:
            if pstdev(minutes)>MINUTES_VOLATILITY_LIMIT:
                reasons.append("VOLATILE_LAST5_MINUTES")
            if abs(mean(minutes[-3:])-mean(minutes))>MINUTES_TREND_LIMIT:
                reasons.append("CHANGING_RECENT_MINUTES_ROLE")
    if opportunity.get("status")!="HISTORICAL_OPPORTUNITY_CANDIDATE":
        reasons.append("MISSING_PREGAME_MINUTES_USAGE_CHALLENGER")
    # Verified report and actual lineup are separate signals. Unknown status
    # is a risk flag, not proof a player is OUT.
    if injury_status!="OFFICIAL_SAME_DAY_VERIFIED":
        reasons.append("NO_VERIFIED_SAME_DAY_INJURY_REPORT")
    return {"status":"PAPER_ELIGIBLE_RESEARCH_ONLY" if not reasons else
                "RESEARCH_ABSTAIN_UNVALIDATED_INPUT",
            "eligible":not reasons,
            "reasons":reasons,
            "history_games":len(historical),
            "thresholds":{"min_prior_games":MIN_PRIOR_GAMES,
                          "max_recent_minutes_sd":MINUTES_VOLATILITY_LIMIT,
                          "max_recent_minutes_trend":MINUTES_TREND_LIMIT},
            "probability_calibrated":False,
            "wager_recommended":False}

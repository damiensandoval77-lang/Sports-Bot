"""Research-only hypothetical EV arithmetic for actual sportsbook prices.

EV is only as reliable as the probability used. Sports-Bot currently supplies
uncalibrated experimental residual estimates; therefore NO actionable +EV or
validated edge is claimed. Price must be tied to the EXACT quoted line/side.
"""
import math

METHOD="UNCALIBRATED_MODEL_HYPOTHETICAL_EV"

def american_profit_per_unit(odds):
    """Net winnings for one unit staked, excluding returned principal."""
    if isinstance(odds,bool):raise ValueError("Boolean is not a price")
    price=int(odds)
    if price>=100:return price/100.0
    if price<=-100:return 100.0/abs(price)
    raise ValueError("Invalid American price; expected >=+100 or <=-100")

def implied_probability(odds):
    return 1.0/(1.0+american_profit_per_unit(odds))

def no_vig_probabilities(over_odds,under_odds):
    over=implied_probability(over_odds)
    under=implied_probability(under_odds)
    total=over+under
    return {"over":over/total,"under":under/total,"total_implied":total}

def hypothetical_ev(odds,p_win,p_lose,p_push=0):
    """Return EV per unit stake, negative loss for a losing bet, zero on push.

    An EV of +0.05 means theoretical +0.05 per $1 stake, NOT realized profit.
    """
    p=[float(p_win),float(p_lose),float(p_push)]
    if not all(math.isfinite(v) and 0<=v<=1 for v in p):
        raise ValueError("Invalid probability")
    if abs(sum(p)-1)>0.005:
        raise ValueError("Win/loss/push probabilities must sum to one")
    return p[0]*american_profit_per_unit(odds)-p[1]

def hypothetical_quote_analysis(quote,probability_function,projection,residuals):
    """Separate EV by bookmaker price AND bookmaker's own numeric line."""
    line=float(quote["line"])
    probs=probability_function(projection,line,residuals)
    fair=no_vig_probabilities(quote["over"],quote["under"])
    over=hypothetical_ev(quote["over"],probs["over"],probs["under"],probs["push"])
    under=hypothetical_ev(quote["under"],probs["under"],probs["over"],probs["push"])
    return dict(quote,
        over_model_probability=round(probs["over"],4),
        under_model_probability=round(probs["under"],4),
        push_model_probability=round(probs["push"],4),
        market_no_vig_over=round(fair["over"],4),
        market_no_vig_under=round(fair["under"],4),
        hypothetical_over_ev_pct=round(100*over,2),
        hypothetical_under_ev_pct=round(100*under,2),
        ev_method=METHOD,
        ev_verified=False)

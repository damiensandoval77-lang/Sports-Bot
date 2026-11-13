"""EARLY-SAMPLE edge research from already graded pregame picks.

No claim of calibration or verified advantage: original-model grades on only
two event dates are transferred cautiously to combined-model simulations.
This adjustment is pre-registered and capped, NOT fitted for apparent profits.
Real +EV claims still require independent chronological validation.
"""
import math
from datetime import datetime, timezone

STATS = ("PTS", "REB", "AST", "PRA")
PRIOR_MARKETS = 150
PRIOR_DATES = 8
MAX_CORRECTION = 0.08
METHOD = "TWO_DATE_ORIGINAL_GRADED_ERROR_SHRUNK_COMBINED_SIM_RESEARCH_V1"

def preliminary_probability(sim_rate, stat, audit):
    """Small descriptive correction of a raw combined bootstrap hit frequency."""
    try:
        p=float(sim_rate)
        if not math.isfinite(p) or not 0 <= p <= 1 or stat not in STATS:
            raise ValueError("Invalid input")
        bucket=audit["by_stat"][stat]
        n=int(bucket["sample_size"])
        dates=int(bucket["distinct_event_dates"])
        observed=float(bucket["observed_hit_rate"])
        predicted=float(bucket["average_estimated_probability"])
        if n <= 0: raise ValueError("No observations")
        if not 0<=observed<=1 or not 0<=predicted<=1 or dates<1:
            raise ValueError("Invalid source")
    except (TypeError,KeyError,ValueError,AttributeError):
        return None
    # A few days of correlated markets must exert very limited influence.
    weight=(n/(n+PRIOR_MARKETS))*(dates/(dates+PRIOR_DATES))
    correction=max(-MAX_CORRECTION,min(MAX_CORRECTION,(observed-predicted)*weight))
    return {"probability":round(min(.995,max(.005,p+correction)),4),
            "raw_probability":round(p,4), "correction":round(correction,4),
            "sample_size":n,"distinct_event_dates":dates,
            "source":"ORIGINAL_MODEL_GRADED_PICK_PROBABILITY_ERRORS",
            "method":METHOD,"validated":False}

def preliminary_edge(row, paper, now=None, prizepicks=False):
    """Review-only exact-priced upside, including integer-line push probability.

    No picks may be marked verified. Missing prices lead to probability-only
    output, not fictitious PrizePicks or sportsbook returns.
    """
    now=now or datetime.now(timezone.utc)
    sim=row.get("combined_simulation") or {}
    p=sim.get("selected_hit_rate")
    side=str(row.get("combined_direction") or "").upper()
    base={"status":"INSUFFICIENT_PRELIMINARY_DATA","method":METHOD,
          "verified_edge":False,"probability":None,"net_ev_pct":None,
          "quote":None,"reason":"Insufficient pregame-locked data"}
    if sim.get("simulation_count")!=20000 or sim.get("calibrated") is not False or side not in ("OVER","UNDER") or p is None:
        return base
    audit=paper.get("probability_audit") if isinstance(paper,dict) else None
    if not isinstance(audit,dict) or audit.get("original_model_only") is not True:
        return base
    # Never use a later result or same-day postgame grade for an earlier prop.
    try:
        published=datetime.fromisoformat(paper["generated_at"].replace("Z","+00:00"))
        starts=datetime.fromisoformat(row["start"].replace("Z","+00:00"))
        if (published.tzinfo is None or starts.tzinfo is None or
            published>=starts or starts<=now):
            return base
        completed=paper.get("pipeline_health",{}).get("latest_completed_player_game_date")
        if completed and completed>=starts.date().isoformat():
            return base
    except (KeyError,ValueError,TypeError):
        return base
    adjusted=preliminary_probability(p,row.get("stat"),audit)
    if not adjusted:return base
    result={**base,"status":"PRELIMINARY_PROBABILITY_ONLY","probability":adjusted,
        "reason":"Early-sample adjustment is unvalidated; exact price required"}
    if prizepicks:
        return {**result,"status":"PRIZEPICKS_SLIP_PAYOUT_REQUIRED",
            "reason":"Cannot compute single-leg sportsbook EV from PrizePicks tiers"}
    if row.get("reliability_screen",{}).get("status")!="MODEL_LEAN":
        return {**result,"status":"PASS_STRUCTURAL_SCREEN",
                "reason":"Player or projection fails the structural research screen"}
    quotes=[]
    for quote in row.get("book_quotes") or []:
        try:
            if abs(float(quote["line"])-float(row["line"]))>1e-8:
                continue
            time=datetime.fromisoformat(str(quote["updated_at"]).replace("Z","+00:00"))
            age=(now-time).total_seconds()/60
            if time.tzinfo is None or not 0<=age<=30:continue
            price=quote["over"] if side=="OVER" else quote["under"]
            if isinstance(price,bool):continue
            price=float(price)
            if price>=100:profit=price/100
            elif price<=-100:profit=100/abs(price)
            else:continue
            push=float(sim.get("push_rate") or 0)
            if not 0<=push<=1 or adjusted["probability"]+push>1:continue
            ev=adjusted["probability"]*profit-(1-adjusted["probability"]-push)
            quotes.append({"book":quote["name"],"line":float(quote["line"]),
                           "side":side,"odds":int(price),"updated_at":quote["updated_at"],
                           "break_even_probability":round(1/(1+profit),4),
                           "net_ev_pct":round(100*ev,2)})
        except (KeyError,ValueError,TypeError,OverflowError):
            continue
    if not quotes:return result
    best=max(quotes,key=lambda q:q["net_ev_pct"])
    return {**result,"status":"PROVISIONAL_POSITIVE_EV" if best["net_ev_pct"]>0
            else "PROVISIONAL_NONPOSITIVE_EV",
            "quote":best,"net_ev_pct":best["net_ev_pct"],
            "reason":"Preliminary hypothetical EV; not calibrated or verified"}

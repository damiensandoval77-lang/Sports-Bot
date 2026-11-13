"""Pure adapter for two PBP Stats WOWY Type=Player responses.

No HTTP. Source data requires separately verified usage permission.
Aggregate response does NOT prove which games were sampled. Independently
verified game dates and historical cutoffs are mandatory.
"""
from datetime import date
try:
    from .lineup_onoff_research import positive,utc
    from .pbpstats_request_plan import request_plan
except ImportError:
    from lineup_onoff_research import positive,utc
    from pbpstats_request_plan import request_plan

METRICS={"PTS":"Points","REB":"Rebounds","AST":"Assists"}

def _rows(payload,target):
    if not isinstance(payload,dict) or not isinstance(payload.get("multi_row_table_data"),list):
        raise ValueError("Missing PBP Stats multi_row_table_data")
    matches=[r for r in payload["multi_row_table_data"]
             if isinstance(r,dict) and str(r.get("EntityId"))==str(target)]
    if len(matches)!=1:
        raise ValueError("Target EntityId not unique in PBP Stats player rows")
    return matches[0]

def _aggregate(payload,target,provenance,cutoff,expected_request):
    row=_rows(payload,target)
    if not isinstance(provenance,dict) or provenance.get("verified_completed_games") is not True:
        raise ValueError("Game-level provenance has not been verified")
    # The two historical provider responses must be bound to their exact
    # target ON/OFF params, including FromDate and ToDate. Do not allow
    # a current-season aggregate to masquerade as a pregame dated query.
    if provenance.get("request_params")!=expected_request:
        raise ValueError("Provider request provenance lacks exact historical date filters")
    raw_dates=provenance.get("game_dates")
    if not isinstance(raw_dates,list) or len(raw_dates)<5:
        raise ValueError("At least five independent game dates are required")
    try:
        dates=[date.fromisoformat(d) for d in raw_dates]
    except (ValueError,TypeError):
        raise ValueError("Invalid completed game dates")
    if len(set(dates))!=len(dates):
        raise ValueError("Duplicate completed game dates")
    if any(d>cutoff for d in dates):
        raise ValueError("Future game dates cannot enter pregame samples")
    seconds=positive(row.get("SecondsPlayed"))
    mins=positive(row.get("Minutes"))
    # Prefer explicit SecondsPlayed units; cross-check optional Minutes.
    if seconds is not None:
        minutes=seconds/60.
        if mins is not None and abs(minutes-mins)>2:
            raise ValueError("Inconsistent provider SecondsPlayed and Minutes")
    else:
        minutes=mins
    if minutes is None or minutes<=0:
        raise ValueError("Missing verified exposure minutes")
    rates={}
    for market,field in METRICS.items():
        total=positive(row.get(field))
        if total is None:raise ValueError("Missing or invalid "+field)
        rates[market+"_per36"]=round(36*total/minutes,6)
    return {"games":len(dates),"minutes":round(minutes,4),**rates}

def normalize_pair(with_payload,without_payload,*,player_id,teammate_id,
                   team,season,provider_generated_at,observed_through_at,
                   data_through,with_provenance,without_provenance):
    """Require the provider query pair and independent game-level provenance.

    Do not attribute post-tip full-season results to an earlier pretip game.
    """
    try:
        cutoff=date.fromisoformat(str(data_through))
        seen=utc(observed_through_at)
        generated=utc(provider_generated_at)
    except (ValueError,TypeError):
        raise ValueError("Invalid provider observation metadata")
    if seen>generated or cutoff>seen.date():
        raise ValueError("Observations cannot postdate source generation")
    plan=request_plan(player_id,teammate_id,team,season,cutoff_date=cutoff.isoformat())
    on=_aggregate(with_payload,player_id,with_provenance,cutoff,plan["requests"]["with"])
    off=_aggregate(without_payload,player_id,without_provenance,cutoff,plan["requests"]["without"])
    return {"player_id":str(player_id),"teammate_id":str(teammate_id),
        "team":str(team).upper(),"season":season,"data_through":cutoff.isoformat(),
        "observed_through_at":seen.isoformat(),"with":on,"without":off}

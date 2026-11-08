"""Licensed, dated on/off splits -> immutable pretip NBA shadow predictions.

This module does NOT scrape or call PBP Stats. It accepts a normalized,
rights-verified provider export and fails closed if its license, timestamps,
IDs, samples or availability context are unverified. It never modifies live
picks, stored locked pregame projections, or simulated hit percentages.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import math

MARKETS=("PTS","REB","AST","PRA")
MIN_GAMES_EACH=5
MIN_MINUTES_EACH=120
MAX_RELATIVE_CHANGE=.08
BLEND=.25

def utc(value):
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("Timezone-aware timestamp required")
    return dt.astimezone(timezone.utc)

def positive(value):
    if value is None or isinstance(value,bool):return None
    try:
        v=float(value)
        return v if math.isfinite(v) and v>=0 else None
    except (TypeError,ValueError,OverflowError):return None

def evaluate(feed, *,player_id,team,teammate_id,market,baseline,
             expected_minutes,game_start,captured_at):
    """Only candidate for ONE official OUT teammate and exact signed IDs.

    Provider-normalized format:
    {status:'LICENSED_ON_OFF_VERIFIED', licensed_use_verified:true,
     source:'provider name', generated_at:ISO,
     observations:[{player_id,teammate_id,team,season:'2026-27',
       data_through:'YYYY-MM-DD', with:{games,minutes,PTS_per36,...},
       without:{games,minutes,PTS_per36,...}}]}.
    """
    result={"status":"UNAVAILABLE_NO_LICENSED_ONOFF_DATA","projection":None,
            "research_only":True,"production_applied":False,
            "confidence_calibrated":False,"player_id":str(player_id),
            "teammate_id":str(teammate_id),"market":market}
    if market not in MARKETS:return dict(result,status="UNSUPPORTED_MARKET")
    baseline=positive(baseline);mins=positive(expected_minutes)
    if baseline is None or mins is None or not 0<mins<=48:
        return dict(result,status="INVALID_BASELINE_OR_MINUTES")
    if not isinstance(feed,dict) or feed.get("status")!="LICENSED_ON_OFF_VERIFIED" or feed.get("licensed_use_verified") is not True:
        return result
    # A provider assertion alone is not a license: require an independently
    # reviewed manifest tying the permitted purpose to our specific bot.
    authorization=feed.get("authorization")
    if (not isinstance(authorization,dict)
        or authorization.get("reviewed_for_betting_analytics") is not True
        or authorization.get("allowed_use")!="NBA_PROP_RESEARCH"
        or authorization.get("reviewer_confirmation")!="MANUALLY_VERIFIED"
        or not str(authorization.get("permission_reference","")).strip()):
        return dict(result,status="MISSING_VERIFIED_USAGE_PERMISSION")
    try:
        captured=utc(captured_at);tip=utc(game_start);issued=utc(feed["generated_at"])
        if not issued<=captured<tip:
            return dict(result,status="UNSAFE_CAPTURE_OR_FEED_TIMESTAMP")
        day=tip.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except (ValueError,KeyError,TypeError,OverflowError):
        return dict(result,status="UNSAFE_CAPTURE_OR_FEED_TIMESTAMP")
    rows=[r for r in feed.get("observations",[]) if isinstance(r,dict)
          and str(r.get("player_id"))==str(player_id)
          and str(r.get("teammate_id"))==str(teammate_id)
          and str(r.get("team"))==str(team)
          and r.get("season")=="2026-27"]
    # Conflicting records are not arbitrarily selected or averaged.
    if len(rows)!=1:return dict(result,status="MISSING_OR_AMBIGUOUS_PLAYER_TEAM_PAIR")
    r=rows[0]
    # The normalized feed must identify each split's *actual* end-of-data
    # timestamp, not just the JSON generation time.
    try:
        observed_through=utc(r["observed_through_at"])
        if observed_through>issued or observed_through>captured:
            return dict(result,status="UNSAFE_SOURCE_OBSERVATION_TIMESTAMP")
    except (KeyError,TypeError,ValueError):
        return dict(result,status="MISSING_SOURCE_OBSERVATION_TIMESTAMP")
    cutoff=r.get("data_through")
    if not isinstance(cutoff,str) or len(cutoff)!=10 or not cutoff<day:
        return dict(result,status="SPLIT_INCLUDES_TARGET_GAME")
    try:
        datetime.strptime(cutoff,"%Y-%m-%d")
    except ValueError:
        return dict(result,status="INVALID_SPLIT_DATE")
    with_group=r.get("with");without_group=r.get("without")
    if not isinstance(with_group,dict) or not isinstance(without_group,dict):
        return dict(result,status="MISSING_ON_OFF_GROUP")
    for group in (with_group,without_group):
        n=group.get("games")
        exposure=positive(group.get("minutes"))
        if (not isinstance(n,int) or isinstance(n,bool) or n<MIN_GAMES_EACH
            or exposure is None or exposure<MIN_MINUTES_EACH):
            return dict(result,status="INSUFFICIENT_ON_OFF_SAMPLE")
    stats=("PTS","REB","AST") if market=="PRA" else (market,)
    deltas=[]
    for stat in stats:
        a=positive(with_group.get(stat+"_per36"))
        b=positive(without_group.get(stat+"_per36"))
        if a is None or b is None:return dict(result,status="MISSING_PER36_RATE")
        deltas.append(b-a)
    raw_per_game=sum(deltas)*mins/36
    # Small observational splits are shrinkage candidates, not causal effects.
    # Pre-set 25% coefficient and bounded change protect against huge spikes.
    proposal=baseline+BLEND*raw_per_game
    delta=max(1,baseline)*MAX_RELATIVE_CHANGE
    candidate=round(max(0,min(baseline+delta,max(baseline-delta,proposal))),4)
    return {**result,"status":"PREGAME_LICENSED_ON_OFF_SHADOW",
        "projection":candidate,"baseline":round(baseline,4),
        "raw_per_game_difference":round(raw_per_game,4),
        "with_games":with_group["games"],"without_games":without_group["games"],
        "with_minutes":with_group["minutes"],"without_minutes":without_group["minutes"],
        "expected_minutes":round(mins,3),"data_through":cutoff,
        "source":feed.get("source"),"generated_at":feed["generated_at"],
        "method":"FIXED_25PCT_ON_OFF_RATE_BLEND_CAPPED_8PCT_NONCAUSAL",
        "license_verified":True}

"""Pregame-only passing/rebounding tracking opportunity challengers.

Input must be an explicitly authorized provider's completed, dated per-game
tracking observations. Not an NBA.com scraper, and never treats a box-score
assist or rebound as a *potential assist* or *rebound chance*.

A single snapshot is generated before tipoff, then graded against the exact
frozen sportsbook line. Unlicensed/missing/repeated/future data fail closed.
"""
import math
from datetime import date
from statistics import median,pstdev

MARKETS={"AST":("potential_assists","assists"),"REB":("rebound_chances","rebounds")}
MIN_GAMES=8
MIN_MINUTES=160
BLEND=.25
MAX_DELTA=.12

def num(x):
    if x is None or isinstance(x,bool):return None
    try:
        v=float(x)
        return v if math.isfinite(v) and v>=0 else None
    except (ValueError,TypeError,OverflowError):return None

def evaluate(feed,*,player_id,team,market,event_date,baseline,
             expected_minutes,captured_at):
    result={"status":"UNAVAILABLE_AUTHORIZED_TRACKING","projection":None,
            "research_only":True,"live_applied":False,
            "probability_calibrated":False}
    if market not in MARKETS:return {**result,"status":"UNSUPPORTED_MARKET"}
    if not isinstance(feed,dict) or feed.get("status")!="AUTHORIZED_TRACKING_RESEARCH" or feed.get("licensed_use_verified") is not True:
        return result
    permission=feed.get("authorization") or {}
    if (permission.get("allowed_use")!="NBA_PROP_RESEARCH" or
        permission.get("reviewer_confirmation")!="MANUALLY_VERIFIED" or
        not str(permission.get("permission_reference","")).strip()):
        return {**result,"status":"MISSING_USAGE_PERMISSION"}
    if feed.get("season")!="2026-27":
        return {**result,"status":"INVALID_SEASON"}
    try:
        from .paper_pick_pipeline import utc
    except ImportError:
        from paper_pick_pipeline import utc
    try:
        from datetime import datetime,timezone
        issued=utc(feed["generated_at"]);captured=utc(captured_at)
        day=date.fromisoformat(str(event_date))
        if issued>captured or (captured-issued).total_seconds()>72*3600:
            raise ValueError("future or stale feed")
        if day<captured.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date():
            return {**result,"status":"EVENT_ALREADY_PASSED"}
    except (ValueError,KeyError,TypeError):
        return {**result,"status":"UNSAFE_SOURCE_TIMESTAMP"}
    baseline=num(baseline);minutes=num(expected_minutes)
    if baseline is None or minutes is None or not 10<=minutes<=42:
        return {**result,"status":"MISSING_PREGAME_MINUTES"}
    field,made=MARKETS[market]
    selected={}
    if not isinstance(feed.get("observations"),list):
        return {**result,"status":"MISSING_TRACKING_GAME_LOGS"}
    for row in feed["observations"]:
        if not isinstance(row,dict):continue
        if str(row.get("player_id"))!=str(player_id) or str(row.get("team"))!=str(team):continue
        game_day=row.get("game_date")
        if not isinstance(game_day,str):return {**result,"status":"INVALID_GAME_DATE"}
        try:prior=date.fromisoformat(game_day)
        except ValueError:return {**result,"status":"INVALID_GAME_DATE"}
        if prior>=day:return {**result,"status":"LOOKAHEAD_REJECTED"}
        try:observed=utc(row["observed_at"])
        except (KeyError,TypeError,ValueError):return {**result,"status":"UNVERIFIED_OBSERVATION_TIME"}
        if observed>issued or observed>captured:
            return {**result,"status":"LOOKAHEAD_REJECTED"}
        played=num(row.get("minutes"));chances=num(row.get(field));converted=num(row.get(made))
        if played is None or not 5<=played<=60 or chances is None or converted is None or converted>chances:
            return {**result,"status":"INVALID_OPPORTUNITY_METRICS"}
        gid=str(row.get("game_id",""))
        if not gid.isdecimal() or len(gid)!=10:
            return {**result,"status":"INVALID_GAME_ID"}
        if gid in selected:
            return {**result,"status":"DUPLICATE_GAME_ID"}
        selected[gid]=(game_day,played,chances,converted)
    rows=sorted(selected.values(),key=lambda v:v[0])
    if len(rows)<MIN_GAMES or sum(v[1] for v in rows)<MIN_MINUTES:
        return {**result,"status":"INSUFFICIENT_TRACKING_SAMPLE","prior_games":len(rows)}
    if len(set(r[0] for r in rows))!=len(rows):
        return {**result,"status":"DUPLICATE_GAME_DATE"}
    if pstdev([r[1] for r in rows[-5:]])>8:
        return {**result,"status":"VOLATILE_MINUTES"}
    total_minutes=sum(v[1] for v in rows)
    season_chance_rate=sum(v[2] for v in rows)/total_minutes
    recent_chance_rate=median([v[2]/v[1] for v in rows[-5:]])
    chance_rate=.65*season_chance_rate+.35*recent_chance_rate
    # Shrink unstable finishing/conversion to a bounded season-long rate.
    total_chances=sum(v[2] for v in rows)
    conversion=sum(v[3] for v in rows)/total_chances if total_chances>0 else None
    if conversion is None:
        return {**result,"status":"NO_TRACKED_CHANCES"}
    conversion=min(1.,max(0.,conversion))
    expected_chances=minutes*chance_rate
    raw=expected_chances*conversion
    blended=baseline+BLEND*(raw-baseline)
    allowed=MAX_DELTA*max(1.,baseline)
    estimate=round(max(0.,max(baseline-allowed,min(baseline+allowed,blended))),4)
    return {**result,"status":"PREGAME_TRACKING_OPPORTUNITY_SHADOW",
            "projection":estimate,"unblended_projection":round(raw,4),
            "expected_chances":round(expected_chances,4),
            "observed_conversion_rate":round(conversion,4),
            "prior_games":len(rows),"prior_latest_game":rows[-1][0],
            "expected_minutes":round(minutes,3),
            "source":str(feed.get("source","AUTHORIZED_PROVIDER")),
            "feature":field,"strictly_prior_games":True}

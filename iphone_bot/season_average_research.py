"""Season-average research candidate; never overwrites the trained AI forecast.

The existing gradient-boosted models already consume recency-weighted _Season
features. This is a separate chronological test of whether a true arithmetic
current-season per-game average improves the locked combined projection.
"""
from math import isfinite
from statistics import mean

MARKETS=("PTS","REB","AST","PRA")
METHOD="RESEARCH_80_PERCENT_COMBINED_20_PERCENT_TRUE_SEASON_AVG"
WEIGHT=0.20
MIN_GAMES=5

def positive_number(value):
    if isinstance(value,bool):return None
    try:
        number=float(value)
        return number if isfinite(number) and number>=0 else None
    except (ValueError,TypeError,OverflowError):
        return None

def season_candidate(history,as_of,team,market,combined):
    """Past-only same-team per-game arithmetic average; no retroactive outcomes."""
    base={"method":METHOD,"status":"INSUFFICIENT_PREGAME_SEASON_GAMES",
          "season_games":0,"season_average":None,"research_projection":None,
          "last_observed_date":None,"production_applied":False}
    if market not in MARKETS:return {**base,"status":"UNSUPPORTED_MARKET"}
    forecast=positive_number(combined)
    if forecast is None:return {**base,"status":"INVALID_COMBINED_PROJECTION"}
    games={}
    conflicted=set()
    for row in history:
        if row.get("team")!=team:continue
        date=str(row.get("date",""))
        if len(date)!=10 or date>=as_of:continue
        n=positive_number(row.get(market))
        if market=="PRA" and n is None:
            components=[positive_number(row.get(k)) for k in ("PTS","REB","AST")]
            if all(x is not None for x in components):n=sum(components)
        if n is None:continue
        if date in games and games[date]!=n:conflicted.add(date)
        games[date]=n
    for date in conflicted:games.pop(date,None)
    days=sorted(games)
    if len(days)<MIN_GAMES:
        return {**base,"season_games":len(days),
                "last_observed_date":days[-1] if days else None}
    avg=mean(games[d] for d in days)
    candidate=(1-WEIGHT)*forecast+WEIGHT*avg
    return {**base,"status":"RESEARCH_CANDIDATE_NOT_VALIDATED",
            "season_games":len(days),"season_average":round(avg,3),
            "research_projection":round(max(0,candidate),3),
            "last_observed_date":days[-1]}

def report(records):
    """Only grade research forecasts genuinely locked in new pre-tip snapshots."""
    chosen={}
    for row in sorted(records,key=lambda r:r.get("captured_at","")):
        data=row.get("season_average_challenger")
        if not isinstance(data,dict) or data.get("method")!=METHOD:continue
        if data.get("status")!="RESEARCH_CANDIDATE_NOT_VALIDATED":continue
        try:
            from .paper_pick_pipeline import utc
        except ImportError:
            from paper_pick_pipeline import utc
        try:
            if utc(row["captured_at"])>=utc(row["event_start"]):continue
        except (KeyError,ValueError,TypeError):continue
        key=(utc(row["event_start"]).isoformat(),str(row.get("player_id")),
             str(row.get("team")),str(row.get("market")))
        chosen.setdefault(key,row)
    n=0;hits=0;baseline_hits=0;mae=0.0;baseline_mae=0.0
    pending=0
    for row in chosen.values():
        if row.get("status")!="SETTLED":
            pending+=1
            continue
        challenger=positive_number(row["season_average_challenger"].get("research_projection"))
        baseline=positive_number(row.get("combined_projection"))
        actual=positive_number(row.get("actual"))
        line=positive_number(row.get("line"))
        if None in (challenger,baseline,actual,line):continue
        n+=1
        mae+=abs(challenger-actual)
        baseline_mae+=abs(baseline-actual)
        if actual!=line:
            hits+=int((challenger>line)==(actual>line)) if challenger!=line else 0
            baseline_hits+=int((baseline>line)==(actual>line)) if baseline!=line else 0
    return {"method":METHOD,"research_only":True,"live_model_unchanged":True,
            "locked_markets":len(chosen),"settled":n,"pending":pending,
            "challenger_mae":round(mae/n,3) if n else None,
            "combined_mae":round(baseline_mae/n,3) if n else None,
            "challenger_direction_wins":hits,"baseline_direction_wins":baseline_hits,
            "note":"Prospective descriptive challenge; no retrospective fitting or probability calibration"}

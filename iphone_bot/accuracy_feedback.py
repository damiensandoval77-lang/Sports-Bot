"""Research-only accuracy feedback on frozen pregame NBA model forecasts.

No model is fitted, changed, selected, or weighted here. One earliest
pregame bookmaker observation represents each player/event/stat. Chronological
splits are by entire UTC event DATE to avoid same-game train/test overlap.
"""
from collections import defaultdict
from datetime import datetime
from statistics import mean
try:
    from .model_performance import independent_rows, forecast_values, finite, utc, MODEL_NAMES
except ImportError:
    from model_performance import independent_rows, forecast_values, finite, utc, MODEL_NAMES

MARKETS=("PTS","REB","AST","PRA")
MIN_EARLIER=30
MIN_LATER=15
MIN_DATES=6


def eligible_rows(records):
    """Only independently graded, locked, finite, all-model observations."""
    rows=[]
    for row in independent_rows(records):
        forecasts=forecast_values(row)
        actual=finite(row.get("actual"))
        if (actual is None or actual<0 or
                any(forecasts[m] is None or forecasts[m]<0 for m in MODEL_NAMES)):
            continue
        try:
            start=utc(row["event_start"])
            capture=utc(row["captured_at"])
            if capture>=start:continue
        except (ValueError,TypeError,KeyError):
            continue
        rows.append({"date":start.date().isoformat(),
                     "event_start":start.isoformat(),
                     "player_id":str(row.get("player_id","")),
                     "market":str(row.get("market","")),
                     "actual":actual,"predictions":forecasts})
    return sorted(rows,key=lambda r:(r["date"],r["event_start"],r["player_id"],r["market"]))


def metrics(rows):
    n=len(rows)
    mae={}
    bias={}
    for model in MODEL_NAMES:
        errors=[r["predictions"][model]-r["actual"] for r in rows]
        mae[model]=round(mean(abs(e) for e in errors),3) if errors else None
        bias[model]=round(mean(errors),3) if errors else None
    delta=(mae["combined"]-mae["original"]
           if mae["combined"] is not None else None)
    return {"observations":n,"distinct_game_dates":len({r["date"] for r in rows}),
            "mae":mae,"signed_bias":bias,
            "combined_minus_original_mae":round(delta,3) if delta is not None else None}


def chronological_split(rows,min_earlier=MIN_EARLIER,min_later=MIN_LATER,
                        min_dates=MIN_DATES):
    """Use full event dates; require sufficient earlier and later observations."""
    days=sorted({r["date"] for r in rows})
    if len(days)<min_dates or len(rows)<min_earlier+min_later:
        return None
    # Nearest boundary to 75% earlier/25% later, with both sample minima.
    choices=[]
    for day in days[1:]:
        earlier=[r for r in rows if r["date"]<day]
        later=[r for r in rows if r["date"]>=day]
        if len(earlier)<min_earlier or len(later)<min_later:
            continue
        choices.append((abs(len(earlier)-0.75*len(rows)),day,earlier,later))
    return min(choices,key=lambda t:(t[0],t[1])) if choices else None


def describe_market(rows):
    overall=metrics(rows)
    split=chronological_split(rows)
    result={"status":"INSUFFICIENT_CHRONOLOGICAL_SAMPLE",
            "overall":overall,"earlier":None,"later_holdout":None,
            "later_start_date":None,"earlier_end_date":None,
            "minimum_earlier":MIN_EARLIER,"minimum_later":MIN_LATER,
            "minimum_distinct_dates":MIN_DATES,
            "heldout_better_model":None,
            "validated_for_live_use":False}
    if split is None:return result
    _,day,earlier,later=split
    result.update(status="DESCRIPTIVE_CHRONOLOGICAL_HOLDOUT",
                  earlier=metrics(earlier),later_holdout=metrics(later),
                  earlier_end_date=max(r["date"] for r in earlier),
                  later_start_date=day)
    # Do not select a model on the later holdout! Return comparisons only.
    return result


def evaluate(records):
    rows=eligible_rows(records)
    grouped=defaultdict(list)
    for row in rows:
        if row["market"] in MARKETS:grouped[row["market"]].append(row)
    return {
        "status":"RESEARCH_ONLY_CHRONOLOGICAL_ACCURACY_FEEDBACK",
        "method":"ONE_EARLIEST_LOCKED_BOOK_PER_PLAYER_EVENT_STAT; FULL_DATE_CHRONOLOGICAL_HOLDOUT",
        "common_sample_only":True,
        "overall":describe_market(rows),
        "by_stat":{market:describe_market(grouped[market]) for market in MARKETS},
        "live_model_unchanged":True,
        "production_weight_adjustment_applied":False,
        "limitations":[
            "Every observed error uses a forecast saved before the scheduled game.",
            "Original, opponent-aware and combined projections use identical settled markets.",
            "All examples from one game date stay on the same side of the chronological boundary.",
            "The later holdout is descriptive and is never used to select a new production model.",
            "Player games and points/rebounds/assists/PRA are correlated; samples are not independent wagers.",
            "No claims of probability calibration, guaranteed pick accuracy, or live model improvement."
        ]
    }

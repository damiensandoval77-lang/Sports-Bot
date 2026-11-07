"""Research-only calibration audit of frozen ORIGINAL-AI prop probabilities.

The experimental hit percentage is generated from original-model historical
residuals, NOT combined-model forecasts. Test the matching original direction
on independent completed player/game/stat markets; never backfill a missing
past probability, never treat duplicate books as independent observations.
"""
from collections import defaultdict
from datetime import datetime, timezone
import math

MARKETS=("PTS","REB","AST","PRA")
BINS=((0,0.5),(0.5,0.6),(0.6,0.7),(0.7,0.8),(0.8,0.9),(0.9,1.00000001))
METHOD="ORIGINAL_MODEL_LOCKED_QUOTE_PROBABILITY_VS_COMPLETED_REAL_PROP"


def utc(value):
    v=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if v.tzinfo is None:raise ValueError("timestamp has no timezone")
    return v.astimezone(timezone.utc)


def finite(value):
    if value is None or isinstance(value,bool):return None
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None


def eligible(records):
    grouped=defaultdict(list)
    rejected=defaultdict(int)
    for row in records:
        if row.get("status")!="SETTLED":
            rejected["unsettled"]+=1
            continue
        try:
            capture=utc(row["captured_at"])
            start=utc(row["event_start"])
        except (KeyError,ValueError,TypeError):
            rejected["invalid_capture_time"]+=1
            continue
        if capture>=start:
            rejected["late_capture"]+=1
            continue
        p=finite(row.get("original_probability_estimate"))
        original=finite(row.get("original_projection"))
        line=finite(row.get("line"))
        actual=finite(row.get("actual"))
        if p is None:
            rejected["missing_original_probability"]+=1
            continue
        if p<0 or p>1 or any(x is None for x in (original,line,actual)):
            rejected["invalid_probability_or_stat"]+=1
            continue
        if original==line or actual==line:
            rejected["no_direction_or_push"]+=1
            continue
        side="OVER" if original>line else "UNDER"
        if row.get("original_probability_side")!=side:
            rejected["probability_side_mismatch"]+=1
            continue
        if row.get("original_probability_method")!="CHRONOLOGICAL_VALIDATION_EMPIRICAL_RESIDUALS_UNCALIBRATED":
            rejected["unverified_probability_method"]+=1
            continue
        key=(str(row["player_id"]),start.isoformat(),str(row["market"]))
        grouped[key].append((capture,str(row.get("bookmaker","")).casefold(),row,p,side,actual,line))
    result=[]
    for group in grouped.values():
        capture,book,row,p,side,actual,line=min(group,key=lambda x:(x[0],x[1],x[6]))
        outcome=int((actual>line)==(side=="OVER"))
        result.append({"date":utc(row["event_start"]).date().isoformat(),
                       "market":str(row["market"]),"estimated":p,"won":outcome,
                       "player_id":str(row["player_id"]),
                       "event_start":utc(row["event_start"]).isoformat()})
    result.sort(key=lambda r:(r["event_start"],r["player_id"],r["market"]))
    return result,dict(rejected)


def summarize(rows):
    n=len(rows)
    if not n:
        return {"sample_size":0,"wins":0,"losses":0,"observed_hit_rate":None,
                "average_estimated_probability":None,"calibration_gap":None,
                "brier_score":None,"mean_absolute_probability_error":None,
                "distinct_event_dates":0}
    predicted=sum(r["estimated"] for r in rows)/n
    actual=sum(r["won"] for r in rows)/n
    return {"sample_size":n,"wins":sum(r["won"] for r in rows),
            "losses":n-sum(r["won"] for r in rows),
            "observed_hit_rate":round(actual,4),
            "average_estimated_probability":round(predicted,4),
            "calibration_gap":round(actual-predicted,4),
            "brier_score":round(sum((r["estimated"]-r["won"])**2 for r in rows)/n,4),
            "mean_absolute_probability_error":round(sum(abs(r["estimated"]-r["won"]) for r in rows)/n,4),
            "distinct_event_dates":len({r["date"] for r in rows})}


def audit(records):
    observations,rejected=eligible(records)
    buckets=[]
    for low,high in BINS:
        segment=[r for r in observations if low<=r["estimated"]<high]
        item=summarize(segment)
        item.update(label=f"{int(low*100)}–{int(min(high,1)*100)}%",
                    lower=low,upper=min(1.0,high),
                    sufficient_sample=len(segment)>=30)
        buckets.append(item)
    by_market={market:summarize([r for r in observations if r["market"]==market])
               for market in MARKETS}
    overall=summarize(observations)
    return {"status":"DESCRIPTIVE_PROBABILITY_CALIBRATION_ONLY",
            "method":METHOD,
            "probability_source":"LOCKED_ORIGINAL_AI_EXPERIMENTAL_RESIDUAL_PROBABILITY",
            "original_model_only":True,
            "not_combined_model_probability":True,
            "no_live_calibration_applied":True,
            "sufficient_overall_sample":overall["sample_size"]>=100 and overall["distinct_event_dates"]>=6,
            "overall":overall,"bins":buckets,"by_stat":by_market,
            "excluded":rejected,
            "limitations":[
                "Original-model probabilities are evaluated only against the original-model predicted direction.",
                "The Combined AI uses a different directional forecast; its win-loss record is reported separately.",
                "One earliest pregame eligible sportsbook quote represents each player/game/stat.",
                "Unsettled games, tied lines, missing or invalid probabilities, and late picks are excluded.",
                "Observed frequencies are descriptive; small buckets can vary greatly by chance.",
                "No probability recalibration or changes to the live model are performed."]}

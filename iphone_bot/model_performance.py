"""Out-of-sample descriptive performance on pregame-locked NBA prop forecasts.

Only SETTLED observations with a real pregame quote and actual completed stat.
Each player/game/market appears once per model to avoid weighting duplicate books
as independent predictions. No model refitting, market calibration or real wagers.
"""
from collections import defaultdict
from datetime import datetime,timezone
import math

def utc(value):
    d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('Missing timezone')
    return d.astimezone(timezone.utc)

MODEL_NAMES=("original","opponent_aware","combined")

def finite(x):
    try:
        n=float(x)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError):
        return None

def price_profit(odds):
    n=int(odds)
    if n>=100:return n/100
    if n<=-100:return 100/abs(n)
    raise ValueError("Invalid price")

def forecast_values(row):
    base=finite(row.get("original_projection"))
    shadow=finite(row.get("opponent_shadow_projection"))
    locked_combined=finite(row.get("combined_projection"))
    # Never backfill prior records from revised models or future game results.
    # If original and shadow projections were locked pregame, their midpoint
    # is mathematically reconstructable from those SAME stored predictions.
    if locked_combined is not None:
        combined=locked_combined
    elif base is not None and shadow is not None:
        combined=(base+shadow)/2
    else:
        combined=None
    return {"original":base,"opponent_aware":shadow,
            "combined":combined if shadow is not None else None}

def quote_side_price(row,side):
    """Use exact pregame price for this direction, or report unavailable."""
    key="over_odds" if side=="OVER" else "under_odds"
    odds=row.get(key)
    if odds is None:
        # Legacy ledger only preserved a price for the originally selected side.
        odds=row.get("american_odds") if side==row.get("side") else None
    if odds is None:return None
    try:return price_profit(odds)
    except (ValueError,TypeError,OverflowError):return None

def independent_rows(records):
    groups=defaultdict(list)
    for r in records:
        if r.get("status")!="SETTLED":continue
        if finite(r.get("actual")) is None or finite(r.get("line")) is None:continue
        if not r.get("captured_at") or not r.get("event_start"):continue
        try:
            if utc(r["captured_at"])>=utc(r["event_start"]):continue
            event=utc(r["event_start"]).isoformat()
        except (ValueError,TypeError):continue
        key=(str(r.get("player_id")),event,str(r.get("market")))
        groups[key].append(r)
    # Stable earliest available price, one representative quote per prop/event.
    return [sorted(group,key=lambda r:(str(r["captured_at"]),str(r.get("bookmaker","")).casefold(),
                                           float(r["line"])))[0]
            for _,group in sorted(groups.items())]


def paired_model_comparison(records, minimum_sample=30):
    """Compare all three frozen models on the exact same completed props.

    This is descriptive evidence, NOT a significance test or a claim of
    calibrated probabilities. Related props may remain correlated.
    """
    eligible=[]
    for row in independent_rows(records):
        forecasts=forecast_values(row)
        actual=finite(row.get("actual"))
        line=finite(row.get("line"))
        if actual is None or line is None or any(forecasts[m] is None for m in MODEL_NAMES):
            continue
        eligible.append((row,forecasts,actual,line))

    def describe(subset):
        n=len(subset)
        if not n:
            return {"sample_size":0,"sufficient_sample":False,
                    "mae":{m:None for m in MODEL_NAMES},
                    "combined_mae_change_vs_original":None,
                    "combined_mae_change_vs_opponent_aware":None,
                    "direction":{m:{"wins":0,"losses":0,"pushes":0,"hit_rate":None}
                                 for m in MODEL_NAMES},
                    "all_models_direction_eligible":0}
        maes={m:sum(abs(f[m]-a) for _,f,a,_ in subset)/n for m in MODEL_NAMES}
        direction={m:{"wins":0,"losses":0,"pushes":0,"hit_rate":None} for m in MODEL_NAMES}
        common=0
        for _,forecasts,actual,line in subset:
            if actual!=line and all(forecasts[m]!=line for m in MODEL_NAMES):
                common+=1
            for m in MODEL_NAMES:
                predicted=forecasts[m]
                if predicted==line:continue
                if actual==line:direction[m]["pushes"]+=1
                elif (predicted>line)==(actual>line):direction[m]["wins"]+=1
                else:direction[m]["losses"]+=1
        for m in MODEL_NAMES:
            d=direction[m]
            total=d["wins"]+d["losses"]
            d["hit_rate"]=round(d["wins"]/total,4) if total else None
        return {
            "sample_size":n,
            "sufficient_sample":n>=minimum_sample,
            "mae":{m:round(v,3) for m,v in maes.items()},
            "combined_mae_change_vs_original":round(maes["combined"]-maes["original"],3),
            "combined_mae_change_vs_opponent_aware":round(maes["combined"]-maes["opponent_aware"],3),
            "direction":direction,
            "all_models_direction_eligible":common,
        }
    return {
        "status":"DESCRIPTIVE_PAIRED_RESEARCH_ONLY",
        "minimum_sample_for_display":minimum_sample,
        "overall":describe(eligible),
        "by_stat":{stat:describe([r for r in eligible if r[0].get("market")==stat])
                   for stat in ("PTS","REB","AST","PRA")},
        "interpretation":"Negative combined MAE change means smaller average error on the SAME games; it does not establish profitability or statistical significance.",
        "live_model_unchanged":True,
    }

def compute_performance(records,include_breakdown=True):
    chosen=independent_rows(records)
    models={}
    for name in MODEL_NAMES:
        evaluated=[]
        graded=[]
        for row in chosen:
            prediction=forecast_values(row)[name]
            if prediction is None:continue
            actual=float(row["actual"]);line=float(row["line"])
            evaluated.append((abs(prediction-actual),row))
            if prediction==line or actual==line:
                # Prediction tie has no side; result at the exact line is a push.
                if prediction!=line and actual==line:
                    graded.append(("PUSH",0.0,True))
                continue
            side="OVER" if prediction>line else "UNDER"
            actual_side="OVER" if actual>line else "UNDER"
            win=side==actual_side
            payout=quote_side_price(row,side)
            graded.append(("WIN" if win else "LOSS",
                           (payout if win else -1.0) if payout is not None else None,
                           payout is not None))
        wins=sum(item[0]=="WIN" for item in graded)
        losses=sum(item[0]=="LOSS" for item in graded)
        pushes=sum(item[0]=="PUSH" for item in graded)
        priced=[item[1] for item in graded if item[2] and item[1] is not None]
        models[name]={
            "observations":len(evaluated),
            "mae":round(sum(x[0] for x in evaluated)/len(evaluated),3) if evaluated else None,
            "direction_eligible":wins+losses,
            "direction_wins":wins,"direction_losses":losses,
            "direction_pushes":pushes,
            "direction_hit_rate":round(wins/(wins+losses),4) if wins+losses else None,
            "priced_paper_selections":len(priced),
            "paper_profit_units":round(sum(priced),4),
            "paper_roi_per_priced_unit":round(sum(priced)/len(priced),4) if priced else None,
        }
    per_stat={}
    if include_breakdown:
        for stat in ("PTS","REB","AST","PRA"):
            matches=[row for row in chosen if row.get("market")==stat]
            per_stat[stat]=compute_performance(matches,include_breakdown=False)["models"]
    return {"status":"PREGAME_FORECASTS_GRADED_AGAINST_REAL_BOXSCORES",
            "method":"ONE_EARLIEST_QUOTED_BOOK_PER_PLAYER_EVENT_MARKET",
            "independent_settled_markets":len(chosen),
            "models":models,
            "by_stat":per_stat,
            "paired_comparison":paired_model_comparison(records) if include_breakdown else None,
            "limitations":[
                "Models use their original pregame-locked predictions; no after-game model reruns.",
                "Legacy combined midpoint may be derived only from two stored pregame forecasts, not postgame data.",
                "Each player/event/stat is counted once; related player props remain statistically correlated.",
                "Paper ROI uses actual recorded pregame prices for the model's exact direction; unavailable prices are excluded.",
                "An unpriced opposite side is not assumed to have the stored originally selected side's odds.",
                "A model tied with the market line has no directional selection.",
                "Outcomes tied to the market line are pushes and excluded from hit-rate denominator.",
                "Paper results are NOT actual placed bets and cannot demonstrate a reliable edge with small samples.",
            ]}

"""Chronological weight experiments on locked pregame original/shadow projections.

Research only. Never adjusts live combined picks or retrofits historical locks.
Candidate weights are chosen on older completed games, then evaluated on
later untouched test games, with a minimum data requirement.
"""
from collections import defaultdict
from statistics import mean

CANDIDATES=(0.0,0.25,0.5,0.75,1.0)
TRAIN_MIN=50
TEST_MIN=20

def walkforward_weights(records):
    try:
        from .model_performance import independent_rows,finite,utc
    except ImportError:
        from model_performance import independent_rows,finite,utc
    grouped=defaultdict(list)
    for r in independent_rows(records):
        original=finite(r.get("original_projection"))
        shadow=finite(r.get("opponent_shadow_projection"))
        actual=finite(r.get("actual"))
        if None in (original,shadow,actual):continue
        grouped[str(r.get("market"))].append((utc(r["event_start"]),original,shadow,actual))
    outputs={}
    for stat in ("PTS","REB","AST","PRA"):
        rows=sorted(grouped.get(stat,[]),key=lambda x:x[0])
        # Group by tipoff date to avoid testing on contemporaneous outcomes
        # that have already leaked into a sibling training observation.
        days=sorted(set(row[0].date() for row in rows))
        ntest=max(TEST_MIN,len(rows)//4)
        if len(rows)<TRAIN_MIN+TEST_MIN or len(days)<6:
            outputs[stat]={"status":"INSUFFICIENT_WALKFORWARD_SAMPLES",
                           "observations":len(rows),"required":TRAIN_MIN+TEST_MIN,
                           "selected_original_weight":None,"test_mae":None}
            continue
        boundary=None
        for day in days:
            test=[r for r in rows if r[0].date()>=day]
            train=[r for r in rows if r[0].date()<day]
            if len(train)>=TRAIN_MIN and len(test)>=TEST_MIN and len(test)>=ntest:
                boundary=day
        if boundary is None:
            outputs[stat]={"status":"INSUFFICIENT_DISTINCT_GAME_DATES",
                           "observations":len(rows),"selected_original_weight":None,"test_mae":None}
            continue
        train=[r for r in rows if r[0].date()<boundary]
        test=[r for r in rows if r[0].date()>=boundary]
        def mae(rows,w):return mean(abs((w*r[1]+(1-w)*r[2])-r[3]) for r in rows)
        selected=min(CANDIDATES,key=lambda w:(mae(train,w),abs(w-.5)))
        outputs[stat]={"status":"OUT_OF_SAMPLE_RESEARCH_ONLY",
                       "observations":len(rows),"training_count":len(train),
                       "test_count":len(test),"test_start":boundary.isoformat(),
                       "selected_original_weight":selected,
                       "selected_shadow_weight":round(1-selected,2),
                       "train_mae":round(mae(train,selected),3),
                       "test_mae":round(mae(test,selected),3),
                       "equal_weight_test_mae":round(mae(test,.5),3),
                       "original_test_mae":round(mae(test,1),3),
                       "shadow_test_mae":round(mae(test,0),3),
                       "applied_to_live_model":False}
    return {"status":"CHRONOLOGICAL_RESEARCH_NOT_PRODUCTION",
            "weights":outputs,
            "method":"Choose on earlier dates, test on later dates; 50+ training, 20+ test per market.",
            "live_model_unchanged":True}

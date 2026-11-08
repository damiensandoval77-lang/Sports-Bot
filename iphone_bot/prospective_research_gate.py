"""Prospective research capture completeness gate.

Legacy rows may correctly lack newer diagnostics. Never backfill them
retroactively. A *newly captured* row must freeze the three diagnostic
results (including honest 'insufficient inputs' statuses), or its associated
board publish should fail before any new research file is committed.
"""
from collections import Counter

FIELDS=("sanity_shadow_v1","stress_test_20k_v1","model_disagreement_v1")

def inspect(rows,before,after):
    if before>after:raise ValueError("Research ledger shrank")
    new=rows[before:after]
    missing=Counter()
    status_by_field={k:Counter() for k in FIELDS}
    for row in new:
        for field in FIELDS:
            d=row.get(field)
            if not isinstance(d,dict) or not d.get("status"):
                missing[field]+=1
            else:
                status_by_field[field][str(d["status"])]+=1
    return {"new_research_rows":len(new),
            "all_new_rows_have_three_diagnostics":not any(missing.values()),
            "missing_by_field":dict(missing),
            "by_diagnostic_status":{k:dict(v) for k,v in status_by_field.items()},
            "missing_history_does_not_imply_retroactive_rebuild":True,
            "missing_input_status_is_not_calibrated_confidence":True}

def verify(rows,before,after):
    result=inspect(rows,before,after)
    if not result["all_new_rows_have_three_diagnostics"]:
        raise AssertionError("New prospective research rows missing mandatory frozen diagnostics: "+
                             str(result["missing_by_field"]))
    return result

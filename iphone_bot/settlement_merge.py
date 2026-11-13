"""Merge independent NBA settlement results with newest GitHub main safely.

A settlement run may race with pregame capture. Never replace the current
ledger with an earlier checkout. Retain earliest immutable pregame data,
upgrade PENDING -> SETTLED only after matching verified outcomes, and keep
previous terminal states. Recalculate published aggregate from merged ledger.
"""
import json
import sys
from collections import Counter
from pathlib import Path

try:
    from .paper_pick_pipeline import identity,summary,utc
except ImportError:
    from paper_pick_pipeline import identity,summary,utc

TERMINAL={"SETTLED","VOID_DNP","INVALID_LATE_CAPTURE"}

def read_records(path):
    p=Path(path)
    if not p.exists():return []
    value=json.loads(p.read_text())
    if not isinstance(value,dict) or not isinstance(value.get("records"),list):
        raise ValueError("Invalid paper ledger data")
    return value["records"]


def merge(base,new):
    """First capture wins. New settled data may only update old pending states."""
    saved={}
    for row in sorted(base,key=lambda r:utc(r["captured_at"])):
        k=identity(row)
        if k not in saved:saved[k]=dict(row)
    for row in sorted(new,key=lambda r:utc(r["captured_at"])):
        k=identity(row)
        if k not in saved:
            saved[k]=dict(row)
            continue
        original=saved[k]
        if original.get("status") in TERMINAL:continue
        if row.get("status") in TERMINAL:
            # Preserve original immutable line, bookmaker, timestamp,
            # projection, side and odds while bringing in result-only fields.
            preserve={k:original.get(k) for k in (
                "event_start","captured_at","player_id","player","team",
                "game","market","bookmaker","line","side",
                "american_odds","over_odds","under_odds",
                "original_projection","combined_projection",
                "opponent_shadow_projection","model_feature_audit",
                "frozen_minutes_research","frozen_minutes_v2_research",
                "frozen_injury_status","forensic_data_collected_pregame",
                "original_probability_side",
                "original_probability_estimate",
                "original_probability_method","experimental_estimate")}
            original.update({k:v for k,v in row.items() if k in (
                "status","settled_at","settlement_source","source_game_id",
                "actual","actual_minutes","result","paper_profit_units",
                "void_reason","void_source_url","void_recorded_at")})
            original.update(preserve)
    return sorted(saved.values(),key=lambda r:(
        utc(r["event_start"]),str(r["player_id"]),r["market"],
        r["bookmaker"],utc(r["captured_at"])))


def publish(base_path,settled_path,output_path,summary_path,form_path=None):
    base=read_records(base_path)
    update=read_records(settled_path)
    records=merge(base,update)
    if len(records)<len(base):raise AssertionError("Historical pregame records dropped")
    if len({identity(r) for r in records})!=len(records):
        raise AssertionError("Duplicate market identities after merge")
    Path(output_path).write_text(json.dumps({"version":1,"records":records},indent=2)+"\n")
    source=json.loads(Path(form_path).read_text()) if form_path and Path(form_path).exists() else {}
    report=summary(records,source=source)
    Path(summary_path).write_text(json.dumps(report,indent=2)+"\n")
    return {"count":len(records),"settled":report["settled"],
            "pending":report["pending"],"newly_settled":
                sum(x.get("status")=="SETTLED" for x in records)-
                sum(x.get("status")=="SETTLED" for x in base)}


if __name__=="__main__":
    if len(sys.argv)!=6:
        raise SystemExit("usage: settlement_merge.py current-ledger new-ledger output-ledger output-summary form")
    print(json.dumps(publish(*sys.argv[1:]),sort_keys=True),flush=True)

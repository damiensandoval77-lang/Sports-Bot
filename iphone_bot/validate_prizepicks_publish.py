"""Fail-closed publisher gate for real PrizePicks site snapshots.

Never claims full provider coverage when upstream paginated data is partial.
Only checks whether the candidate export truthfully preserves its own source.
"""
import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

def timestamp(value):
    try:
        t=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None
    except (ValueError,TypeError,OverflowError):
        return None

def validate(raw,site,model,now=None,max_source_age_minutes=360):
    now=now or dt.datetime.now(dt.timezone.utc)
    issues=[]
    if not all(isinstance(x,dict) for x in (raw,site,model)):
        return ["INPUT_NOT_OBJECT"]
    if raw.get("status")!="LIVE_THIRD_PARTY_PRIZEPICKS_LINES" or site.get("status")!=raw.get("status"):
        issues.append("UNVERIFIED_PROVIDER_STATUS")
    if site.get("source")!="independent_prizepicksapi_com":
        issues.append("INVALID_SITE_SOURCE")
    if site.get("generated_at")!=raw.get("generated_at"):
        issues.append("SITE_SOURCE_TIMESTAMP_MISMATCH")
    when=timestamp(raw.get("generated_at"))
    if when is None or (now-when).total_seconds()>max_source_age_minutes*60 or (when-now).total_seconds()>600:
        issues.append("SOURCE_TIMESTAMP_INVALID_OR_STALE")
    board=site.get("board_offers")
    original=raw.get("board_offers")
    if not isinstance(board,list) or not isinstance(original,list) or not board:
        issues.append("EMPTY_OR_INVALID_PROVIDER_BOARD")
        return issues
    valid=[x for x in original if isinstance(x,dict) and x.get("source")=="independent_prizepicksapi_com"
           and x.get("is_demo") is False and x.get("game") and x.get("starts_at")
           and (x.get("more_tier") or x.get("less_tier"))]
    if len(board)!=len(valid) or site.get("independent_board_count")!=len(valid):
        issues.append("VERIFIED_OFFER_COUNT_MISMATCH")
    source_ids=[str(x.get("id")) for x in valid]
    exported_ids=[str(x.get("id")) for x in board if isinstance(x,dict)]
    if sorted(source_ids)!=sorted(exported_ids) or len(exported_ids)!=len(board):
        issues.append("OFFER_IDENTITIES_CHANGED_OR_MISSING")
    source_by_id={str(x.get("id")):x for x in valid}
    for row in board:
        if not isinstance(row,dict):
            continue
        original_row=source_by_id.get(str(row.get("id")))
        if original_row is None or any(row.get(key)!=original_row.get(key) for key in
                ("player","team","game","stat","line","starts_at","observed_at","more_tier","less_tier","source","is_demo")):
            issues.append("EXPORTED_OFFER_DIFFERS_FROM_VERIFIED_SOURCE")
            break
    for row in board:
        if not isinstance(row,dict) or row.get("is_demo") is not False or row.get("source")!="independent_prizepicksapi_com":
            issues.append("UNVERIFIED_EXPORTED_OFFER")
            break
        line=row.get("line")
        if isinstance(line,bool) or not isinstance(line,(int,float)) or not math.isfinite(line) or line<0:
            issues.append("INVALID_EXPORTED_LINE")
            break
    if site.get("partial_board")!=raw.get("partial_board") or site.get("complete_provider_board")!=raw.get("complete_provider_board"):
        issues.append("PROVIDER_COMPLETENESS_MISREPORTED")
    scope=raw.get("board_coverage_scope") or "UNVERIFIED_LEGACY_SCOPE"
    if site.get("board_coverage_scope")!=scope:
        issues.append("PROVIDER_SCOPE_MISREPORTED")
    if site.get("complete_provider_board") is True and scope!="NBA_ACTIVE_STANDARD_TIER_ONLY":
        issues.append("STANDARD_BOARD_COMPLETENESS_NOT_VERIFIED")
    # Research input may have zero eligible future markets after tipoff. It must
    # still not claim model-ready status with fabricated/unverified rows.
    picks=model.get("picks")
    if not isinstance(picks,list):
        issues.append("INVALID_MODEL_PICKS")
    elif model.get("status")=="FRESH_AUTHENTIC_PRIZEPICKS_LINES":
        if not picks or model.get("source_generated_at")!=site.get("generated_at") or model.get("is_live") is not True:
            issues.append("MODEL_READY_WITHOUT_MATCHED_SOURCE")
    if model.get("source")!="AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS" or model.get("real_american_odds_provided") is not False:
        issues.append("MODEL_SOURCE_MISREPRESENTED")
    return list(dict.fromkeys(issues))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",type=Path,default=Path("docs/prizepicks.json"))
    p.add_argument("--site",type=Path,default=Path("docs/prizepicks_site.json"))
    p.add_argument("--model",type=Path,default=Path("docs/prizepicks_model_input.json"))
    args=p.parse_args()
    try:
        raw,site,model=[json.loads(path.read_text()) for path in (args.raw,args.site,args.model)]
    except (OSError,ValueError) as e:
        print("PUBLISH BLOCKED:",type(e).__name__,str(e)[:200])
        return 2
    failures=validate(raw,site,model)
    if failures:
        print("PUBLISH BLOCKED:",",".join(failures))
        return 1
    print("PUBLISH GATE PASS: verified line identities, timestamps, completeness and model handoff")
    return 0

if __name__=="__main__":
    sys.exit(main())

"""Read-only audit of *published frozen picks*, independent of unmatched provider lines.

A provider quote without an eligible forecast is not a published pick. Every
published pick must be immutable, pretip and eventually verified graded/void.
Never infer an outcome from live totals or missing finals.
"""
import datetime as dt
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/"docs"
UTC=dt.timezone.utc
STATS={"PTS","REB","AST","PRA"}
GRADED_SOURCES={"NBA_CDN_FINAL","ESPN_FINAL"}
DNP_SOURCES=GRADED_SOURCES | {"NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
             "VERIFIED_FINAL_BOXSCORE_DNP_CROSSCHECKED",
             "ESPN_FINAL_BOX_ABSENT_INJURY_LISTED"}

def stamp(raw):
    try:
        t=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        return t.astimezone(UTC) if t.tzinfo else None
    except (ValueError,TypeError,OverflowError):
        return None

def identity(x):
    try:
        return (str(x["player_id"]),str(x["team"]),str(x["game"]),
                str(x["start"]),str(x["stat"]))
    except (KeyError,TypeError):
        return None

def version(x):
    try:
        return (*identity(x),float(x["line"]))
    except (KeyError,TypeError,ValueError):
        return None

def same_verified_event(a,b):
    """Compare source-scoped IDs only after exact frozen event identity matches.

    NBA and ESPN assign different IDs to the same fixture. Both rows must
    already pass the trusted-final checks in evaluate; no outcomes are changed.
    """
    if identity(a) is None or identity(a)!=identity(b):return False
    def namespace(row):
        source=row.get("final_source","")
        ident=str(row.get("source_game_id") or "")
        if source.startswith("NBA_") and re.fullmatch(r"00\d{8}",ident):return "NBA"
        if source.startswith("ESPN_") and re.fullmatch(r"4\d{8}",ident):return "ESPN"
        return None
    na,nb=namespace(a),namespace(b)
    if a.get("source_game_id")==b.get("source_game_id"):
        return na==nb
    return {na,nb}=={"NBA","ESPN"}

def evaluate(ledger,finals,now=None):
    now=now or dt.datetime.now(UTC)
    if now.tzinfo is None:raise ValueError("Now must have timezone")
    now=now.astimezone(UTC)
    records=ledger.get("records") if isinstance(ledger,dict) else None
    sources=finals.get("records") if isinstance(finals,dict) else None
    reasons=Counter()
    if ledger.get("status")!="FROZEN_NEW_AI_ALL_MARKET" or not isinstance(records,list) or not records:
        reasons["NO_VALID_FROZEN_PICK_LEDGER"]+=1
        records=records if isinstance(records,list) else []
    if not isinstance(sources,list):
        reasons["NO_VERIFIED_FINAL_LEDGER"]+=1
        sources=[]
    outcomes={}
    for x in sources:
        if not isinstance(x,dict):continue
        k=identity(x)
        if not k:continue
        status=x.get("status")
        if (status=="GRADED" and x.get("final_source") in GRADED_SOURCES and x.get("source_game_id")) or (
            status=="EXCLUDED_VERIFIED_DNP" and x.get("final_source") in DNP_SOURCES and
            x.get("source_game_id") and x.get("verified_dnp_reason") and x.get("actual") is None):
            if k in outcomes and outcomes[k]!=x:
                outcomes[k]=None
                reasons["CONFLICTING_VERIFIED_FINALS"]+=1
            elif k not in outcomes:
                outcomes[k]=x
    seen=set()
    counts=Counter()
    actionable=0
    overdue=0
    bad=[]
    for x in records:
        if not isinstance(x,dict):
            reasons["INVALID_FROZEN_PICK"]+=1
            continue
        key=version(x)
        ts=stamp(x.get("start"));captured=stamp(x.get("captured_at"))
        observed=stamp(x.get("market_updated"))
        if (key is None or key in seen or x.get("pickem_tier")!="standard" or
            x.get("standard_line_two_sided_verified") is not True or
            x.get("stat") not in STATS or
            not ts or not captured or not observed or
            not observed<=captured<ts or
            x.get("research_only") is not True):
            reasons["INVALID_OR_DUPLICATE_FROZEN_PICK"]+=1
            bad.append(key)
            continue
        seen.add(key)
        grade=x.get("grade")
        total=x.get("actual")
        source=x.get("final_source")
        final=outcomes.get(identity(x))
        if grade=="GRADED":
            if (source not in GRADED_SOURCES or not x.get("source_game_id") or
                not isinstance(total,(int,float)) or not math.isfinite(total) or
                not isinstance(x.get("absolute_error"),(int,float)) or
                x.get("direction_hit") not in (True,False,None)):
                reasons["INVALID_VERIFIED_GRADE"]+=1
            else:
                counts["graded"]+=1
                if final is None or final.get("status")!="GRADED":
                    reasons["GRADED_WITHOUT_MATCHING_VERIFIED_FINAL"]+=1
                elif final.get("actual")!=total or not same_verified_event(final,x):
                    reasons["GRADED_FINAL_MISMATCH"]+=1
                side=(x.get("estimated_hit_chance") or {}).get("modeled_direction")
                if side in ("More","Less") and isinstance(x.get("line"),(int,float)):
                    if total==x["line"]:
                        if x.get("direction_hit") is not None:
                            reasons["PUSH_RECORDED_AS_WIN_OR_LOSS"]+=1
                    elif x.get("direction_hit") is not (total>x["line"] if side=="More" else total<x["line"]):
                        reasons["INCORRECT_STANDARD_LINE_DIRECTION_GRADE"]+=1
        elif grade=="EXCLUDED_VERIFIED_DNP":
            if (source not in DNP_SOURCES or not x.get("source_game_id") or
                not x.get("verified_dnp_reason") or total is not None or
                x.get("direction_hit") is not None):
                reasons["INVALID_VERIFIED_DNP"]+=1
            else:
                counts["verified_dnp_excluded"]+=1
                if final is None:
                    counts["dnp_without_independent_forecast_record"]+=1
                elif (final.get("status")!="EXCLUDED_VERIFIED_DNP" or
                      not same_verified_event(final,x)):
                    reasons["DNP_FINAL_MISMATCH"]+=1
        elif grade=="PENDING":
            counts["pending"]+=1
            if final is not None:
                reasons["VERIFIED_FINAL_NOT_APPLIED"]+=1
                actionable+=1
            elif ts < now-dt.timedelta(hours=8):
                reasons["SETTLEMENT_OVERDUE_WITHOUT_VERIFIED_FINAL"]+=1
                overdue+=1
        else:
            reasons["UNKNOWN_GRADE_STATE"]+=1
        counts["frozen_picks"]+=1
    return {
        "checked_at":now.isoformat(),
        "status":"READY" if not reasons else "DEGRADED",
        "complete":not reasons and counts["pending"]==0,
        "reconciled":not reasons,
        "scope":"PUBLISHED_STANDARD_FROZEN_PICKS_ONLY",
        "counts":dict(counts),
        "actionable_verified_finals":actionable,
        "overdue_missing_verified_finals":overdue,
        "issues":dict(sorted(reasons.items())),
        "note":"Provider lines without a validated frozen prediction are not published picks. Every saved pick requires an original pretip line and a verified final or independently crosschecked DNP; live scores never grade bets."
    }

def main():
    def read(name):
        try:return json.loads((ROOT/name).read_text(encoding="utf-8"))
        except (OSError,ValueError):return {}
    result=evaluate(read("lagged_matchup_all_market_ledger.json"),
                    read("ai_forecast_actual_ledger.json"))
    target=ROOT/"dames-picks/published_pick_settlement.json"
    target.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("PUBLISHED_PICK_SETTLEMENT",json.dumps(result))
    return 0 if result["status"]=="READY" else 2

if __name__=="__main__":
    raise SystemExit(main())

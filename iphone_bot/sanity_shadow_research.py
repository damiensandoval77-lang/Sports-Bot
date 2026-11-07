"""Pregame, research-only sanity shadow of the locked Combined AI forecast.

No live board, production pick, simulated probability or sportsbook quote is changed.
All history must precede BOTH the capture date and the event date. Parameters
are fixed heuristics, not fitted or validated improvements.
"""
import json
import math
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
BOARD=ROOT/"docs/ai_comparisons.json"
GAMES=ROOT/"data/nba/current/current_games.json"
LEDGER=ROOT/"docs/sanity_shadow_ledger.json"
STATUS=ROOT/"docs/sanity_shadow_status.json"
ET=ZoneInfo("America/New_York")
MARKETS=("PTS","REB","AST","PRA")
METHOD="FIXED_20PCT_BLEND_ONLY_IF_LARGE_DEVIATION_CAP_10PCT_V1"
MIN_GAMES=5
DEVIATION_THRESHOLD=.20
MAX_ADJUSTMENT=.10
BLEND=.20

def utc(v):
    d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("naive timestamp")
    return d.astimezone(timezone.utc)

def finite(v):
    if v is None or isinstance(v,bool):return None
    try:
        x=float(v)
    except (TypeError,ValueError,OverflowError):return None
    return x if math.isfinite(x) and x>=0 else None

def stat_value(row,market):
    v=finite(row.get(market))
    if market=="PRA":
        parts=[finite(row.get(k)) for k in ("PTS","REB","AST")]
        if all(x is not None for x in parts):
            calc=sum(parts)
            if v is not None and abs(v-calc)>.01:return None
            return calc
    return v

def past_games(history,team,market,event_start,captured_at):
    """Reject even same-date post-capture history and sticky conflicting dates."""
    event_day=utc(event_start).astimezone(ET).date().isoformat()
    capture_day=utc(captured_at).astimezone(ET).date().isoformat()
    cutoff=min(event_day,capture_day)
    year=int(event_day[:4]) if int(event_day[5:7])>=10 else int(event_day[:4])-1
    season_start=f"{year}-10-01"
    values={}
    conflict=set()
    for r in history:
        date=str(r.get("date",""))
        if r.get("team")!=team or len(date)!=10 or not season_start<=date<cutoff:continue
        try:
            datetime.strptime(date,"%Y-%m-%d")
        except ValueError:continue
        v=stat_value(r,market)
        mins=finite(r.get("MIN"))
        if v is None or mins is None or not 0<mins<=60:continue
        item=(v,mins)
        if date in values and values[date]!=item:conflict.add(date)
        if date not in conflict:values[date]=item
    for date in conflict:values.pop(date,None)
    return [(date,*values[date]) for date in sorted(values)]

def shadow(history,*,team,market,baseline,event_start,captured_at,
           minutes_context=None,injury_status=None,injury_source=None):
    p=finite(baseline)
    result={"method":METHOD,"status":"INSUFFICIENT_PREGAME_HISTORY",
        "original_combined_projection":p,"shadow_projection":None,
        "season_average":None,"last5_average":None,"last10_average":None,
        "history_games":0,"minutes_l5":None,"minutes_volatility_l5":None,
        "projected_minutes":None,
        "deviation_pct":None,"warnings":[],"research_only":True,
        "live_applied":False,"simulated_probability_changed":False}
    if market not in MARKETS:return dict(result,status="UNSUPPORTED_MARKET")
    if p is None:return dict(result,status="INVALID_COMBINED_PROJECTION")
    try:
        if utc(captured_at)>=utc(event_start):
            return dict(result,status="LATE_CAPTURE_REJECTED")
        games=past_games(history,team,market,event_start,captured_at)
    except (ValueError,TypeError,KeyError):
        return dict(result,status="INVALID_TIME")
    result["history_games"]=len(games)
    if len(games)<MIN_GAMES:
        result["warnings"]=["INSUFFICIENT_PRIOR_SAME_TEAM_GAMES"]
        return result
    vals=[r[1] for r in games]
    season=mean(vals)
    l5=mean(vals[-5:])
    l10=mean(vals[-10:])
    minutes_l5=mean(r[2] for r in games[-5:])
    minutes_volatility=pstdev(r[2] for r in games[-5:])
    context=minutes_context if isinstance(minutes_context,dict) else {}
    expected=finite(context.get("expected_minutes"))
    result.update(season_average=round(season,3),last5_average=round(l5,3),
                  last10_average=round(l10,3),minutes_l5=round(minutes_l5,2),
                  minutes_volatility_l5=round(minutes_volatility,2),
                  projected_minutes=expected)
    warnings=[]
    last_day=datetime.strptime(games[-1][0],"%Y-%m-%d").date()
    capture_day=datetime.fromisoformat(utc(captured_at).astimezone(ET).date().isoformat()).date()
    if (capture_day-last_day).days>14:
        warnings.append("STALE_PLAYER_HISTORY")
    if minutes_volatility>6:
        warnings.append("HIGH_RECENT_MINUTES_VOLATILITY")
    deviation=(p-season)/season if season>0 else None
    result["deviation_pct"]=round(deviation*100,2) if deviation is not None else None
    if deviation is not None and abs(deviation)>=DEVIATION_THRESHOLD:
        warnings.append("LARGE_SEASON_BASELINE_DEVIATION")
    if expected is None:
        warnings.append("EXPECTED_MINUTES_UNVERIFIED")
    elif abs(expected-minutes_l5)>5:
        warnings.append("EXPECTED_MINUTES_DISAGREE_WITH_RECENT")
    if (str(injury_status).upper()!="AVAILABLE" or
            injury_source!="OFFICIAL_NBA_REPORT"):
        warnings.append("INJURY_OR_LINEUP_UNCERTAINTY")
    # A deterministic shadow ONLY for a large unexplained discrepancy.
    # Minutes disagreement/unknown injury blocks adjustment; flags still surface.
    blocked=("EXPECTED_MINUTES_UNVERIFIED" in warnings or
             "EXPECTED_MINUTES_DISAGREE_WITH_RECENT" in warnings or
             "INJURY_OR_LINEUP_UNCERTAINTY" in warnings or
             "HIGH_RECENT_MINUTES_VOLATILITY" in warnings or
             "STALE_PLAYER_HISTORY" in warnings)
    if deviation is None or abs(deviation)<DEVIATION_THRESHOLD:
        status="NO_LARGE_DEVIATION"
        candidate=p
    elif blocked:
        status="REVIEW_ONLY_UNCERTAIN_INPUTS"
        candidate=None
    else:
        delta=BLEND*(season-p)
        capped=max(-MAX_ADJUSTMENT*p,min(MAX_ADJUSTMENT*max(p,1.0),delta))
        candidate=max(0,p+capped)
        status="SHADOW_CANDIDATE_UNVALIDATED"
    result.update(status=status,shadow_projection=round(candidate,3) if candidate is not None else None,
                  warnings=warnings)
    return result

def identity(row):
    return "|".join((utc(row["event_start"]).isoformat(),str(row["player_id"]),
                     str(row["team"]),str(row["market"])))

def capture(board,games,existing,at):
    captured=utc(at)
    if board.get("status")!="EXPERIMENTAL_NON_CALIBRATED" or board.get("verified_current_matchups") is not True:
        raise ValueError("unverified live board")
    generated=utc(board["generated_at"])
    if not 0<=(captured-generated).total_seconds()<=45*60:
        raise ValueError("board must be pregame, fresh, and not from the future")
    by_id=defaultdict(list)
    for g in games:
        if g.get("id") is not None:by_id[str(g["id"])].append(g)
    records=sorted(existing,key=lambda r:r["captured_at"])
    seen={identity(r) for r in records}
    for item in board.get("comparisons",[]):
        try:
            if item.get("stat") not in MARKETS:continue
            start=utc(item["start"])
            if start<=captured:continue
            pid=str(item["player_id"])
            p=finite(item.get("combined_projection"))
            if p is None:continue
            row={"event_start":start.isoformat(),"captured_at":captured.isoformat(),
                 "player_id":pid,"player":str(item.get("player","")),
                 "team":str(item.get("team","")),"market":item["stat"],
                 "game":str(item.get("game","")),
                 "combined_projection":p,"shadow":shadow(by_id[pid],
                    team=str(item.get("team","")),market=item["stat"],
                    baseline=p,event_start=start,captured_at=captured,
                    minutes_context=item.get("minutes_research"),
                    injury_status=item.get("injury_status"),
                    injury_source=item.get("injury_status_source")),
                 "research_only":True,"production_applied":False}
            key=identity(row)
            if key not in seen:
                records.append(row);seen.add(key)
        except (KeyError,ValueError,TypeError):continue
    return sorted(records,key=lambda r:(r["event_start"],r["player_id"],r["market"]))

def report(records):
    counts=Counter((r.get("shadow") or {}).get("status","UNKNOWN") for r in records)
    warnings=Counter(w for r in records for w in (r.get("shadow") or {}).get("warnings",[]))
    return {"status":"RESEARCH_SHADOW_NOT_VALIDATED",
            "method":METHOD,"locked_independent_player_game_markets":len(records),
            "by_status":dict(counts),"warnings":dict(warnings),
            "no_picks_changed":True,"no_probabilities_changed":True,
            "no_verified_accuracy_improvement":True,
            "note":"Fixed pregame heuristic. Compare against settled outcomes on future dates before any promotion."}

def main():
    board=json.loads(BOARD.read_text())
    games=json.loads(GAMES.read_text())
    old=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    at=datetime.now(timezone.utc).isoformat()
    records=capture(board,games,old,at)
    LEDGER.write_text(json.dumps({"version":1,"records":records},indent=2)+"\n")
    outcome=report(records)
    outcome["generated_at"]=at
    STATUS.write_text(json.dumps(outcome,indent=2)+"\n")
    print(json.dumps(outcome,sort_keys=True))

if __name__=="__main__":main()

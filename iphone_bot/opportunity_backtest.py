"""Strict historical NBA opportunity-model challenge against immutable Combined AI.

This is RETROSPECTIVE research using only player-game rows dated STRICTLY
BEFORE the target game. It is not a pregame-locked alternative forecast:
the experiment was coded after initial games settled. It is not eligible for
claims of prospective performance, probability calibration, or live promotion.

Fixed, cautious candidate:
 - minutes: independent robust V2 on >=8 prior games; otherwise historical
   L3/L5 baseline with >=5 games.
 - rate: recent weighted observed PTS/REB/AST per minute (not current game);
 - points usage proxy: PREVIOUS FGA per minute, shrink/clamp relative to L10;
 - blend candidate back toward the already locked Combined AI; clamp deltas.
No change to deployed projections or probability.
"""
import csv
import json
import math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean,pstdev

try:
    from .minutes_model_v2 import forecast as minutes_v2
    from .research_context import minutes_estimate
    from .model_performance import independent_rows,utc,finite
except ImportError:
    from minutes_model_v2 import forecast as minutes_v2
    from research_context import minutes_estimate
    from model_performance import independent_rows,utc,finite

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"data/nba/current/current_games.json"
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"docs/opportunity_backtest.json"
MARKETS=("PTS","REB","AST","PRA")
MIN_GAMES=5
MAX_DELTA_PCT=.15
BLEND=.25

def safe(x):
    if x is None or isinstance(x,bool):return None
    try:
        n=float(x)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):return None

def histories(games):
    """Deduplicate player/team/day; throw away conflicting rows."""
    grouped=defaultdict(dict)
    for g in games:
        try:
            pid=str(g["id"]);team=str(g["team"]);day=str(g["date"])
            datetime.strptime(day,"%Y-%m-%d")
            mins=safe(g.get("MIN"))
            if mins is None or not 0<mins<=60:continue
            vals={key:safe(g.get(key)) for key in ("PTS","REB","AST","FGA")}
            if any(vals[k] is None for k in ("PTS","REB","AST")):continue
            normalized={"id":pid,"team":team,"date":day,"MIN":mins,**vals}
            key=(pid,team); prior=grouped[key].get(day)
            if prior is None:grouped[key][day]=normalized
            elif prior!=normalized:grouped[key][day]=False
        except (KeyError,TypeError,ValueError):continue
    return {key:[g for _,g in sorted(days.items()) if g]
            for key,days in grouped.items()}

def weighted(values):
    """Fixed past-only rate weighting, no outcome-dependent tuning."""
    if len(values)<MIN_GAMES:return None
    return .5*mean(values[-3:])+.3*mean(values[-5:])+.2*mean(values[-10:])

def opportunity(history,target_date,team):
    past=sorted([g for g in history if
       g["date"]<target_date and g["team"]==team],key=lambda x:x["date"])
    result={"status":"INSUFFICIENT_PRIOR_SAME_TEAM_GAMES",
       "history_games":len(past),"as_of":target_date,
       "expected_minutes":None,"mins_method":None,
       "expected_fga":None,"raw_stat_projections":None}
    if len(past)<MIN_GAMES:return result
    robust=minutes_v2(past,target_date,team)
    mins=safe(robust.get("expected_minutes"))
    method="ROBUST_V2_PAST_ONLY"
    if mins is None:
        mins=safe(minutes_estimate(past,target_date).get("expected_minutes"))
        method="FIVE_GAME_MINUTES_BASELINE_PAST_ONLY"
    if mins is None or mins<=0:return result
    rates={}
    for stat in ("PTS","REB","AST"):
        rate=weighted([g[stat]/g["MIN"] for g in past])
        if rate is None:return result
        rates[stat]=rate
    fga_rows=[g for g in past if g["FGA"] is not None]
    expected_fga=None
    factor=1.
    if len(fga_rows)>=MIN_GAMES:
        attempts=weighted([g["FGA"]/g["MIN"] for g in fga_rows])
        if attempts is not None:
            expected_fga=round(mins*attempts,3)
            base=mean(g["FGA"]/g["MIN"] for g in fga_rows[-10:])
            # Proxy signal only; no inferred confirmed usage/on-off.
            if base>0:factor=max(.9,min(1.1,attempts/base))
    raw={"PTS":mins*rates["PTS"]*factor,
         "REB":mins*rates["REB"],
         "AST":mins*rates["AST"]}
    raw["PRA"]=sum(raw[k] for k in ("PTS","REB","AST"))
    return {**result,"status":"HISTORICAL_OPPORTUNITY_CANDIDATE",
        "expected_minutes":round(mins,3),
        "mins_method":method,"expected_fga":expected_fga,
        "usage_fga_ratio_clamped":round(factor,4),
        "last5_minutes_volatility":round(pstdev([g["MIN"] for g in past[-5:]]),3),
        "raw_stat_projections":{k:round(v,4) for k,v in raw.items()},
        "prior_latest_game_date":past[-1]["date"]}

def candidate(base,raw):
    """Pre-specified conservative 25% exposure, max 15% movement."""
    if base is None or raw is None or base<0 or raw<0:return None
    prediction=base+BLEND*(raw-base)
    span=max(1,base)*MAX_DELTA_PCT
    return max(0,round(min(base+span,max(base-span,prediction)),4))

def stability_candidate(base,raw,context):
    """Separate pretip challenger: shrink opportunity shift on volatile minutes.

    Fixed ex-ante heuristic, NOT an empirically calibrated probability. Fewer
    minutes of reliable rotation history should mean less trust in a large
    opportunity adjustment. Original opportunity candidate stays unchanged.
    """
    basic=candidate(base,raw)
    if basic is None:return None
    volatility=safe(context.get("last5_minutes_volatility")) if isinstance(context,dict) else None
    if volatility is None:return None
    exposure=max(.4,1-min(.6,max(0.,(volatility-3.)/12.)))
    return round(max(0.,base+exposure*(basic-base)),4)

def describe(rows):
    n=len(rows)
    if not n:return {"sample_size":0,"baseline_mae":None,"candidate_mae":None,
        "mae_change":None,"baseline_wins":0,"baseline_losses":0,
        "candidate_wins":0,"candidate_losses":0}
    baseline_error=mean(abs(r["baseline"]-r["actual"]) for r in rows)
    candidate_error=mean(abs(r["candidate"]-r["actual"]) for r in rows)
    def direction(key):
        wins=losses=0
        for r in rows:
            if r["actual"]==r["line"] or r[key]==r["line"]:continue
            if (r[key]>r["line"])==(r["actual"]>r["line"]):wins+=1
            else:losses+=1
        return wins,losses
    bw,bl=direction("baseline");cw,cl=direction("candidate")
    return {"sample_size":n,
        "baseline_mae":round(baseline_error,3),
        "candidate_mae":round(candidate_error,3),
        "mae_change":round(candidate_error-baseline_error,3),
        "baseline_wins":bw,"baseline_losses":bl,
        "candidate_wins":cw,"candidate_losses":cl}

def evaluate(records,games):
    historical=histories(games)
    findings=[]
    gaps=defaultdict(int)
    for r in independent_rows(records):
        if r.get("market") not in MARKETS:continue
        try:
            start=utc(r["event_start"]);captured=utc(r["captured_at"])
            if captured>=start:gaps["late_capture"]+=1;continue
            day=start.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
            pid=str(r["player_id"]);team=str(r["team"]);market=r["market"]
            base=safe(r.get("combined_projection"))
            actual=safe(r.get("actual"));line=safe(r.get("line"))
            if any(v is None for v in (base,actual,line)):
                gaps["missing_model_or_stat"]+=1;continue
            hist=historical.get((pid,team),[])
            opportunity_data=opportunity(hist,day,team)
            if opportunity_data["status"]!="HISTORICAL_OPPORTUNITY_CANDIDATE":
                gaps["insufficient_prior_history"]+=1;continue
            raw=opportunity_data["raw_stat_projections"][market]
            alternative=candidate(base,raw)
            if alternative is None:gaps["invalid_candidate"]+=1;continue
            findings.append({"player":r["player"],"player_id":pid,"team":team,
                "game":r["game"],"game_date_eastern":day,"market":market,
                "baseline":base,"candidate":alternative,
                "actual":actual,"line":line,
                "baseline_absolute_error":round(abs(base-actual),3),
                "candidate_absolute_error":round(abs(alternative-actual),3),
                "candidate_improved":abs(alternative-actual)<abs(base-actual),
                "prior_games":opportunity_data["history_games"],
                "last_prior_game":opportunity_data["prior_latest_game_date"],
                "minutes_pred":opportunity_data["expected_minutes"],
                "minutes_method":opportunity_data["mins_method"],
                "fga_pred":opportunity_data["expected_fga"],
                "usage_proxy":opportunity_data["usage_fga_ratio_clamped"],
                "source":r.get("settlement_source")})
        except (ValueError,TypeError,KeyError):gaps["invalid_row"]+=1
    overall=describe(findings)
    games_sorted=sorted({r["game"] for r in findings})
    return {"status":"RETROSPECTIVE_PAST_ONLY_RESEARCH_NO_LIVE_PROMOTION",
       "model":"FIXED_MINUTES_RATE_FGA_SHRUNK_TO_COMBINED",
       "design":"Strict date-before-target historical player logs; locked Combined AI baseline",
       "live_combined_ai_unchanged":True,
       "live_hit_percentages_unchanged":True,
       "prospective_validation":False,
       "overall":overall,
       "by_market":{m:describe([r for r in findings if r["market"]==m]) for m in MARKETS},
       "by_game":{g:describe([r for r in findings if r["game"]==g]) for g in games_sorted},
       "missing":dict(gaps),
       "retrospective_candidates":len(findings),
       "candidate_improved_markets":sum(x["candidate_improved"] for x in findings),
       "examples":sorted(findings,key=lambda r:(-(r["baseline_absolute_error"]),r["player"],r["market"]))[:36],
       "constraints":{"min_history_games":MIN_GAMES,"candidate_blend":BLEND,
                      "maximum_relative_deviation":MAX_DELTA_PCT,
                      "future_game_information_used":False,
                      "verified_teammate_out_adjustments_used":False,
                      "fga_usage_proxy_is_not_usage_rate":True},
       "limitations":["Retrospective comparison was constructed after these games settled.",
        "Only games dated before the target are used; no target game statistics enter the alternative.",
        "No claim of causal injury or teammate effects; injury-specific promotions require separately captured pregame scenarios.",
        "Same-player points, rebounds, assists, and PRA are correlated observations.",
        "Report only: no tuned weights, betting profitability or calibrated probabilities.",
        "A later genuinely pregame-locked shadow cohort is mandatory before promoting this candidate."]}

def main():
    records=json.loads(LEDGER.read_text()).get("records",[])
    try:
        games=json.loads(INPUT.read_text()) if INPUT.exists() else []
    except (ValueError,OSError):games=[]
    report=evaluate(records,games)
    report["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(report,indent=2)+"\n")
    print("OPPORTUNITY RESEARCH:",json.dumps({
        "overall":report["overall"],"by_market":report["by_market"],
        "coverage":report["missing"],"prospective_validation":False},sort_keys=True),flush=True)

if __name__=="__main__":main()

"""Defender-aware points *research*, NOT a deployed projection.

Consumes independently sourced NBA LeagueSeasonMatchups rows with offensive
and defensive player IDs. Defenders must also be on an independently verified
opponent rotation; historical contact does not prove a future assignment.
Samples are shrunk toward offensive baseline. No use of game-day outcomes,
unknown minutes, or imaginary defensive matchups.
"""
import json
import math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data/nba/research/defender_matchups.json"
REPORT=ROOT/"docs/defender_v3_research.json"
MIN_PAIR_POSSESSIONS=20
MIN_TOTAL_POSSESSIONS=75
SHRINK_FGA=80.0
MAX_EFFICIENCY_SHIFT=.12
MAX_POINTS_SHIFT=.08


def finite(x):
    if x is None or isinstance(x,bool):return None
    try:
        n=float(x)
        return n if math.isfinite(n) and n>=0 else None
    except (TypeError,ValueError):return None


def clean_matchup(row):
    """Parse NBA LeagueSeasonMatchups spelling, reject mismatched FG counts."""
    try:
        offense=str(row["OFF_PLAYER_ID"]).strip()
        defender=str(row["DEF_PLAYER_ID"]).strip()
        possession=finite(row["PARTIAL_POSS"])
        attempts=finite(row["MATCHUP_FGA"])
        made=finite(row["MATCHUP_FGM"])
        minutes=finite(row["MATCHUP_MIN"])
        if not offense.isdigit() or not defender.isdigit() or offense==defender:
            return None
        if None in (possession,attempts,made,minutes):
            return None
        if possession<=0 or attempts>possession or made>attempts or minutes<=0:
            return None
        return {"off_id":offense,"def_id":defender,"poss":possession,
                "fga":attempts,"fgm":made,"minutes":minutes}
    except (KeyError,TypeError,ValueError):
        return None


def defender_scenario(off_id,opponent_defender_ids,rows,offense_fg_pct,
                      baseline_points,as_of,source_through,rotation_verified=False):
    """Estimate research-only scoring efficiency effect, never side or hit %.

    The rotation must be independently verified; absent it, no assignment
    is presumed. Historical exposures are normalized over observed defender
    matchups to avoid incorrectly treating them as true future fractions.
    """
    result={"status":"MATCHUP_DATA_UNAVAILABLE","projection":None,
            "baseline_points":baseline_points,"adjustment_points":None,
            "defenders":[],"estimated_exposure_method":"HISTORICAL_POSS_SHARE_NOT_PROJECTED_ASSIGNMENT",
            "live_applied":False,"validated_for_live_use":False}
    try:
        asof=datetime.fromisoformat(str(as_of).replace("Z","+00:00"))
        through=datetime.fromisoformat(str(source_through).replace("Z","+00:00"))
    except (ValueError,TypeError):
        return {**result,"status":"INVALID_SOURCE_DATES"}
    if asof.tzinfo is None or through.tzinfo is None or through>=asof:
        return {**result,"status":"SOURCE_NOT_STRICTLY_PREGAME"}
    baseline=finite(baseline_points)
    fg=finite(offense_fg_pct)
    if baseline is None or fg is None or not (.2<=fg<=.75):
        return {**result,"status":"INVALID_OFFENSIVE_BASELINE"}
    if not rotation_verified:
        return {**result,"status":"OPPONENT_ROTATION_UNVERIFIED"}
    defenders={str(x).strip() for x in opponent_defender_ids if str(x).strip().isdigit()}
    if not defenders:return {**result,"status":"NO_VERIFIED_DEFENDERS"}
    groups=defaultdict(lambda:{"poss":0.0,"fga":0.0,"fgm":0.0,"mins":0.0})
    for raw in rows:
        parsed=clean_matchup(raw)
        if not parsed or parsed["off_id"]!=str(off_id) or parsed["def_id"] not in defenders:
            continue
        group=groups[parsed["def_id"]]
        for field,key in (("poss","poss"),("fga","fga"),("fgm","fgm"),("mins","minutes")):
            group[field]+=parsed[key]
    eligible={key:g for key,g in groups.items() if g["poss"]>=MIN_PAIR_POSSESSIONS}
    total=sum(g["poss"] for g in eligible.values())
    if total<MIN_TOTAL_POSSESSIONS:
        return {**result,"status":"INSUFFICIENT_HISTORICAL_MATCHUP_SAMPLE",
                "observed_possessions":round(total,1)}
    overall=0.0
    parts=[]
    for defender,g in sorted(eligible.items(),key=lambda kv:(-kv[1]["poss"],kv[0])):
        exposure=g["poss"]/total
        # Only FG efficiency is modeled here. No causality or foul/3pt inference.
        # Shrink observed matchup efficiency to the OFFENSIVE player's baseline.
        posterior=(g["fgm"]+SHRINK_FGA*fg)/(g["fga"]+SHRINK_FGA)
        shift=max(-MAX_EFFICIENCY_SHIFT,min(MAX_EFFICIENCY_SHIFT,(posterior-fg)/fg))
        overall+=exposure*shift
        parts.append({"def_player_id":defender,
                      "historical_matchup_possessions":round(g["poss"],1),
                      "historical_fga":round(g["fga"],1),
                      "historical_fgm":round(g["fgm"],1),
                      "historical_matchup_fg_pct":round(g["fgm"]/g["fga"],4) if g["fga"] else None,
                      "smoothed_fg_pct":round(posterior,4),
                      "historical_exposure_share":round(exposure,4),
                      "smoothed_efficiency_shift":round(shift,4),
                      "confirmed_primary_defender":False})
    shift=max(-MAX_POINTS_SHIFT,min(MAX_POINTS_SHIFT,overall))
    return {**result,"status":"DEFENDER_RESEARCH_SCENARIO_ONLY",
            "projection":round(baseline*(1+shift),2),
            "baseline_points":round(baseline,2),
            "adjustment_points":round(baseline*shift,2),
            "hypothetical_scoring_shift_pct":round(100*shift,2),
            "observed_possessions":round(total,1),
            "defenders":parts}


def research_status(source_path=SOURCE,output=REPORT):
    """Diagnostic-only output: no pretending that unavailable NBA tracking is live."""
    out={"generated_at":datetime.now(timezone.utc).isoformat(),
         "status":"AWAITING_VERIFIED_NBA_DEFENDER_MATCHUP_SOURCE",
         "source":"NBA LeagueSeasonMatchups endpoint schema",
         "documentation":"https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leagueseasonmatchups.md",
         "live_model_unchanged":True,
         "original_probability_unchanged":True,
         "defender_assignments_confirmed":False,
         "validation":"PENDING_CHRONOLOGICAL_HOLDOUT",
         "scenarios_computed":0,
         "minimum_pair_possessions":MIN_PAIR_POSSESSIONS,
         "minimum_total_possessions":MIN_TOTAL_POSSESSIONS,
         "limitations":[
           "Tracking availability from GitHub Actions and historical date coverage not yet proven.",
           "LeagueSeasonMatchups summarizes historical encounters, not projected next-game assignments.",
           "Defended FG percentage alone does not identify causal defensive ability or possession usage.",
           "No live adjustment without verified rotation and later-game accuracy improvement."]}
    if source_path.exists():
        try:
            data=json.loads(source_path.read_text())
            through=datetime.fromisoformat(str(data["source_through"]).replace("Z","+00:00"))
            rows=data["rows"]
            if through.tzinfo is None or not isinstance(rows,list):raise ValueError("invalid source")
            out["source_through"]=through.isoformat()
            out["valid_matchup_rows"]=sum(clean_matchup(x) is not None for x in rows)
            out["status"]="HISTORICAL_MATCHUP_SOURCE_LOADED_RESEARCH_ONLY" if out["valid_matchup_rows"] else "HISTORICAL_MATCHUP_SOURCE_EMPTY"
        except (ValueError,TypeError,KeyError,AttributeError):
            out["status"]="HISTORICAL_MATCHUP_SOURCE_INVALID"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(out,indent=2)+"\n")
    return out


if __name__=="__main__":
    print(json.dumps(research_status(),indent=2))

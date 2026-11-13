"""2025-26 chronological held-out offensive-involvement research backtest.

Real historical player game results are obtained through the repository's
existing download_archived_nba.py. No NBAstuffer extraction, invented prop
quotes, actual NBA USG%, or production inference changes.

Estimated involvement proxy = (FGA + .44*FTA + TOV)/MIN, not team-possession
USG%. Both the model and baseline consume only same-team PRIOR game logs.
"""
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

try:
    from .shot_profile_research import load_history
except ImportError:
    from shot_profile_research import load_history

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/offensive_involvement_holdout_research.json"
HOLDOUT = "2025-26"
MIN_PRIOR = 8


def weighted(vals):
    if not vals:
        raise ValueError("Empty history")
    return .5*mean(vals[-3:]) + .3*mean(vals[-5:]) + .2*mean(vals[-10:])


def predict(prior):
    """Predeclared blending, no fitting to held-out outcomes."""
    if len(prior) < MIN_PRIOR:
        return None
    recent = prior[-10:]
    if any(row.get(k) is None for row in recent for k in
           ("PTS", "MIN", "FGA", "FTA", "TOV")):
        return None
    if any(row["MIN"] < 1 or row["MIN"] > 60 for row in recent):
        return None
    baseline = weighted([r["PTS"] for r in recent])
    minutes = weighted([r["MIN"] for r in recent])
    # Rate approach preserves observed correlations between a player's
    # offensive opportunities and time on court; it does not infer true usage.
    volume = weighted([(r["FGA"] + .44*r["FTA"] + r["TOV"])/r["MIN"]
                       for r in recent])
    # Shrink efficiency estimate to the full prior sample, not current result.
    prior_volume = sum(r["FGA"]+.44*r["FTA"]+r["TOV"] for r in prior)
    prior_points = sum(r["PTS"] for r in prior)
    if prior_volume <= 0:
        return None
    pts_per_proxy_opp = prior_points/prior_volume
    raw = max(0., minutes*volume*pts_per_proxy_opp)
    # Cap novel effect to 15% of baseline; blend 25% for sensitivity only.
    bound = .15*max(1., baseline)
    challenger = max(0., baseline+.25*max(-bound,min(bound,raw-baseline)))
    return {"baseline": baseline, "challenger": challenger,
            "minutes_projection":minutes, "involvement_proxy":volume,
            "raw_opportunity_projection":raw}


def evaluate(rows, season=HOLDOUT):
    grouped=defaultdict(list)
    for r in rows:
        if r.get("season")==season and r.get("id") and r.get("team") and r.get("date"):
            grouped[(str(r["id"]),r["team"])].append(r)
    paired=[]
    excluded=defaultdict(int)
    for (player_id,team),games in grouped.items():
        dates=defaultdict(list)
        for r in games:
            dates[r["date"]].append(r)
        history=[]
        for day in sorted(dates):
            same_day=dates[day]
            # Multiple player games on the same date are ambiguous. Do not
            # train or grade on one until their identity is resolved.
            if len(same_day)!=1:
                excluded["AMBIGUOUS_PLAYER_DATE"]+=len(same_day)
                continue
            target=same_day[0]
            forecast=predict(history)
            if forecast is None:
                excluded["INSUFFICIENT_PAST_DATA"]+=1
            else:
                actual=target["PTS"]
                if actual is None or not math.isfinite(actual):
                    excluded["INVALID_TARGET"]+=1
                else:
                    paired.append({"date":day,"player_id":player_id,
                        "team":team,"actual":actual,**forecast})
            history.append(target)
    if not paired:
        raise RuntimeError("No matched holdout games: "+json.dumps({"source_rows":len(rows),"player_team_groups":len(grouped),"excluded":dict(excluded),"sample_group_sizes":sorted([len(g) for g in grouped.values()],reverse=True)[:12],"sample_rows":list(rows[:2])},default=str))
    def summarise(sample):
        n=len(sample)
        if not n:
            return {"n":0,"dates":0,"baseline_mae":None,"challenger_mae":None,"mae_difference":None,"baseline_rmse":None,"challenger_rmse":None,"challenger_better_rows":0,"baseline_better_rows":0,"ties":0}
        base=[abs(r["baseline"]-r["actual"]) for r in sample]
        chall=[abs(r["challenger"]-r["actual"]) for r in sample]
        return {"n":n,"dates":len({r["date"] for r in sample}),
            "baseline_mae":round(mean(base),4),
            "challenger_mae":round(mean(chall),4),
            "mae_difference":round(mean(chall)-mean(base),4),
            "baseline_rmse":round(math.sqrt(mean((r["baseline"]-r["actual"])**2 for r in sample)),4),
            "challenger_rmse":round(math.sqrt(mean((r["challenger"]-r["actual"])**2 for r in sample)),4),
            "challenger_better_rows":sum(c<b for c,b in zip(chall,base)),
            "baseline_better_rows":sum(b<c for c,b in zip(chall,base)),
            "ties":sum(b==c for c,b in zip(chall,base))}
    # No tuning based on holdout result. Split by calendar date for robustness.
    midpoint=sorted({r["date"] for r in paired})[len({r["date"] for r in paired})//2]
    first=[r for r in paired if r["date"]<midpoint]
    second=[r for r in paired if r["date"]>=midpoint]
    return {"status":"REAL_HISTORICAL_OFFENSIVE_INVOLVEMENT_HOLDOUT",
        "holdout_season":season,
        "source":"Existing licensed-or-publicly-accessible historical box-score input; usage rights must be independently verified",
        "model":"FIXED_25_PERCENT_BLENDED_FGA_FTA_TOV_PER_MINUTE_OPPORTUNITY_PROXY",
        "feature_label":"OFFENSIVE_INVOLVEMENT_PROXY_NOT_OFFICIAL_USAGE_RATE",
        "overall":summarise(paired),
        "first_half":summarise(first),"second_half":summarise(second),
        "excluded":dict(excluded),
        "sportsbook_lines_used":False,"prop_hit_rate":None,"calibrated":False,
        "production_modified":False,"automatic_promotion":False,
        "limitations":[
          "Retrospective season holdout; candidate specifications fixed before test run.",
          "No verified live betting lines or official NBA USG%; MAE is not pick hit rate.",
          "No injuries or actual on-court defensive assignments inferred.",
          "Only prior same-team games are used; dates with ambiguous duplicate player games excluded.",
          "Positive result would require independent confirmation and prospective validation."]}


def load_history_with_box_context():
    rows,rejected=load_history()
    # Existing shot-profile loader omits TOV even though archived CSV includes it.
    # Join independently by season, player ID, and GAME_ID; never assume zero.
    raw_path=ROOT/"data/nba/raw/raw_game_logs.csv"
    turnover_by_id={}
    with raw_path.open(encoding="utf-8-sig",newline="") as handle:
        reader=csv.DictReader(handle)
        if not {"SEASON_ID","PLAYER_ID","GAME_ID","GAME_DATE","TOV","OREB"}.issubset(reader.fieldnames or ()):
            raise ValueError("Historical archive lacks trusted turnover columns")
        for line in reader:
            key=(line["SEASON_ID"],line["PLAYER_ID"],line["GAME_ID"])
            try:
                t=float(line["TOV"])
                oreb=float(line["OREB"])
            except (ValueError,TypeError):
                continue
            if not math.isfinite(t) or t<0 or not math.isfinite(oreb) or oreb<0:
                continue
            identity=(line["GAME_DATE"],t,oreb)
            if key in turnover_by_id and turnover_by_id[key]!=identity:
                raise ValueError("Conflicting turnover game records")
            turnover_by_id[key]=identity
    matched=0
    for row in rows:
        saved=turnover_by_id.get((row["season"],row["id"],row["game_id"]))
        if saved and saved[0]==row["date"]:
            row["TOV"]=saved[1]
            row["OREB"]=saved[2]
            matched+=1
    print("Verified turnovers and OREB attached to player-games:",matched,"of",len(rows),flush=True)
    return rows,rejected


def main():
    rows,rejected=load_history_with_box_context()
    report=evaluate(rows)
    report["source_rejections"]=rejected
    report["generated_at"]=datetime.now(timezone.utc).isoformat()
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("OFFENSIVE_INVOLVEMENT_HOLDOUT",json.dumps({
        "overall":report["overall"],"first_half":report["first_half"],
        "second_half":report["second_half"],"excluded":report["excluded"],
        "production_modified":report["production_modified"]}),flush=True)


if __name__=="__main__":
    main()

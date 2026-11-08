"""Pregame shot origin and scoring-opportunity research. NO live projection changes.

Only box-score zones are available: 3PA and inferred 2PA=FGA-3PA.
We cannot infer midrange/rim/corner-3 locations, potential assists or tracking
shot quality from this source. All training data precedes the target game.
"""
import math
from collections import defaultdict,deque
from datetime import date,datetime,timezone
from pathlib import Path
from statistics import mean
try:
    from .minutes_model_v2 import forecast as minutes_v2_forecast
except ImportError:
    from minutes_model_v2 import forecast as minutes_v2_forecast

FIELDS=("MIN","FGA","FG3A","FGM","FG3M","FTA","FTM","PTS")
REQUIRED_HISTORY=8
SEASONS=("2022-23","2023-24","2024-25","2025-26")
TEST_SEASON="2025-26"
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"data/nba/raw/raw_game_logs.csv"
OUTPUT=ROOT/"docs/shot_profile_validation.json"


def number(value):
    if isinstance(value,bool):return None
    try: result=float(value)
    except (ValueError,TypeError):return None
    return result if math.isfinite(result) and result>=0 else None


def normalized(game,require_makes=True):
    """Reconstruct the TWO-point bucket; never claim location within the arc."""
    mins=number(game.get("MIN"))
    fga=number(game.get("FGA"))
    three=number(game.get("FG3A"))
    if mins is None or not 0<mins<=60 or fga is None or three is None or three>fga:
        return None
    out={"MIN":mins,"FGA":fga,"FG3A":three,"FG2A":fga-three}
    if not require_makes:return out
    fgm=number(game.get("FGM"))
    fg3m=number(game.get("FG3M"))
    fta=number(game.get("FTA"))
    ftm=number(game.get("FTM"))
    pts=number(game.get("PTS"))
    if None in (fgm,fg3m,fta,ftm,pts):return None
    if fgm>fga or fg3m>three or fg3m>fgm or ftm>fta:return None
    twom=fgm-fg3m
    if twom>fga-three:return None
    # NBA scoring identity. Missing technical foul points / corrections are
    # not silently accepted: this archive should reconstruct exactly.
    if abs(pts-(2*twom+3*fg3m+ftm))>0.01:return None
    return {**out,"FG2M":twom,"FG3M":fg3m,"FTA":fta,"FTM":ftm,"PTS":pts}


def _weighted_mean(xs):
    if not xs:return None
    last3=mean(xs[-3:])
    last5=mean(xs[-5:])
    last10=mean(xs[-10:])
    return .50*last3+.30*last5+.20*last10


def predict_attempts(history,as_of,team,expected_minutes=None):
    """Use past 2P/3P shot frequency per minute, not current game attempts.

    When expected_minutes is unavailable, use past-only 3/5/10-minute blend.
    In production cards this is a descriptive scenario, NOT the live AI.
    """
    past=sorted((g for g in history
                 if isinstance(g.get("date"),str) and g["date"]<as_of
                 and g.get("team")==team),key=lambda r:r["date"])
    valid=[]
    seen=set()
    for g in reversed(past):
        if g["date"] in seen:continue
        seen.add(g["date"])
        obs=normalized(g,require_makes=False)
        if obs:valid.append(obs)
        if len(valid)>=12:break
    valid.reverse()
    out={"status":"INSUFFICIENT_SHOT_HISTORY","expected_minutes":None,
         "expected_fga":None,"expected_3pa":None,"expected_2pa":None,
         "three_point_attempt_share":None,"history_games":len(valid),
         "live_adjustment_applied":False,"is_verified_shot_location":False,
         "three_point_source":"BOX_SCORE_3PA_ONLY"}
    if len(valid)<REQUIRED_HISTORY:return out
    minutes=(number(expected_minutes) if expected_minutes is not None else
             _weighted_mean([g["MIN"] for g in valid]))
    if minutes is None or not 0<minutes<=60:return out
    # Rate per game is less stable when minutes change. First model per-minute
    # attempt rates, with the forward-looking minutes forecast independent of
    # observed target game usage.
    two_rate=_weighted_mean([g["FG2A"]/g["MIN"] for g in valid])
    three_rate=_weighted_mean([g["FG3A"]/g["MIN"] for g in valid])
    two=max(0,minutes*two_rate)
    three=max(0,minutes*three_rate)
    total=two+three
    return {**out,"status":"SHOT_PROFILE_RESEARCH_UNVALIDATED",
            "expected_minutes":round(minutes,2),
            "expected_fga":round(total,2),
            "expected_3pa":round(three,2),
            "expected_2pa":round(two,2),
            "three_point_attempt_share":round(three/total,4) if total else 0,
            "history_games":len(valid)}


def predict_points(history,as_of,team,expected_minutes):
    """Estimate points from 2PA/3PA/FTA and historical makes, strictly pregame.

    Shooting percentages are smoothed with fixed pseudocounts, not fitted
    using the held-out season. The per-minute FTA estimate is independent of
    the predicted 2/3 attempt shares.
    """
    attempts=predict_attempts(history,as_of,team,expected_minutes)
    if attempts["expected_fga"] is None:return None
    valid=[]
    for g in sorted(history,key=lambda x:x.get("date","")):
        if g.get("team")==team and g.get("date","")<as_of:
            obs=normalized(g,require_makes=True)
            if obs:valid.append(obs)
    valid=valid[-12:]
    if len(valid)<REQUIRED_HISTORY:return None
    total2=sum(g["FG2A"] for g in valid)
    made2=sum(g["FG2M"] for g in valid)
    total3=sum(g["FG3A"] for g in valid)
    made3=sum(g["FG3M"] for g in valid)
    totalft=sum(g["FTA"] for g in valid)
    madeft=sum(g["FTM"] for g in valid)
    # Stable league-style priors, NOT observed personal current-game rates.
    pct2=(made2+12*.52)/(total2+12)
    pct3=(made3+12*.35)/(total3+12)
    pctft=(madeft+12*.77)/(totalft+12)
    ft_rate=_weighted_mean([g["FTA"]/g["MIN"] for g in valid])
    fta=attempts["expected_minutes"]*ft_rate
    points=2*attempts["expected_2pa"]*pct2+3*attempts["expected_3pa"]*pct3+fta*pctft
    return {**attempts,"expected_fta":round(fta,2),
            "expected_2p_pct":round(pct2,4),
            "expected_3p_pct":round(pct3,4),
            "expected_ft_pct":round(pctft,4),
            "expected_points":round(points,2),
            "model":"TWO_THREE_FREE_THROW_OPPORTUNITY_RESEARCH_ONLY"}


def load_history(path=ARCHIVE):
    # Revalidate shot fields and historical identity independently; no
    # training feature from any later game is ever used for prediction.
    import csv
    seen={}
    rejected=defaultdict(int)
    with open(path,newline="",encoding="utf-8-sig") as stream:
        rd=csv.DictReader(stream)
        needed={"PLAYER_ID","GAME_ID","GAME_DATE","SEASON_ID","TEAM_ABBREVIATION",*FIELDS}
        if needed-set(rd.fieldnames or []):
            raise ValueError("Missing shot archive columns: "+str(sorted(needed-set(rd.fieldnames or []))))
        for raw in rd:
            season=raw["SEASON_ID"]
            if season not in SEASONS:continue
            day=raw["GAME_DATE"]
            try:
                d=date.fromisoformat(day)
                year=int(season[:4])
                if not date(year,9,1)<=d<=date(year+1,7,31):raise ValueError("Season/date mismatch")
            except ValueError:
                rejected["invalid_date"]+=1;continue
            ident=(season,raw["PLAYER_ID"],raw["GAME_ID"])
            if not raw["PLAYER_ID"].isdigit() or not raw["GAME_ID"] or not raw["TEAM_ABBREVIATION"]:
                rejected["invalid_identity"]+=1;continue
            candidate={k:number(raw[k]) for k in FIELDS}
            if any(v is None for v in candidate.values()):
                rejected["invalid_numbers"]+=1;continue
            # Historical matchup is a schedule descriptor, not a postgame statistic.
            matchup=str(raw.get("MATCHUP") or "")
            opponent=(matchup.split()[-1] if (" vs. " in matchup or " @ " in matchup)
                      else None)
            if opponent and len(opponent)!=3:opponent=None
            # AST and REB are observed archived totals, not tracking chances.
            entry={**candidate,"AST":number(raw.get("AST")),"REB":number(raw.get("REB")),
                   "id":raw["PLAYER_ID"],"game_id":raw["GAME_ID"],
                   "team":raw["TEAM_ABBREVIATION"],"opponent":opponent,
                   "date":day,"season":season}
            if not normalized(entry,require_makes=True):
                rejected["invalid_box_score"]+=1;continue
            if ident in seen:
                if seen[ident]!=entry:raise ValueError("Conflicting duplicate shot box score: "+str(ident))
                rejected["duplicate"]+=1;continue
            seen[ident]=entry
    return list(seen.values()),dict(rejected)


def metrics(samples):
    n=len(samples)
    if not n:return {"observations":0,"players":0,"dates":0,
                     "fga_mae":None,"two_pa_mae":None,"three_pa_mae":None,
                     "points_mae":None,"simple_points_mae":None,"points_mae_change":None}
    def mae(p,a):return round(mean(abs(x[p]-x[a]) for x in samples),3)
    return {"observations":n,"players":len({x["player_id"] for x in samples}),
            "dates":len({x["date"] for x in samples}),
            "fga_mae":mae("predicted_fga","actual_fga"),
            "two_pa_mae":mae("predicted_2pa","actual_2pa"),
            "three_pa_mae":mae("predicted_3pa","actual_3pa"),
            "fta_mae":mae("predicted_fta","actual_fta"),
            "points_mae":mae("predicted_points","actual_points"),
            "simple_points_mae":mae("simple_points","actual_points"),
            "points_mae_change":round(mae("predicted_points","actual_points")-
                                     mae("simple_points","actual_points"),3),
            "opportunity_better":sum(abs(x["predicted_points"]-x["actual_points"])<
                                     abs(x["simple_points"]-x["actual_points"]) for x in samples),
            "simple_better":sum(abs(x["predicted_points"]-x["actual_points"])>
                                abs(x["simple_points"]-x["actual_points"]) for x in samples)}


def evaluate(records):
    """Entire 2025-26 is a predeclared holdout; no later-season calibration."""
    by_player=defaultdict(list)
    for g in records:
        by_player[(g["season"],g["id"],g["team"])].append(g)
    evaluated=[]
    for (season,pid,team),player_games in by_player.items():
        games=sorted(player_games,key=lambda x:(x["date"],x["game_id"]))
        history=deque(maxlen=12)
        for g in games:
            day=g["date"]
            prior=[x for x in history if x["date"]<day]
            if len(prior)>=REQUIRED_HISTORY:
                # Same minutes forecast for all baselines and attempt profiles.
                minute_pred=minutes_v2_forecast(prior,day,team)["expected_minutes"]
                model=predict_points(prior,day,team,minute_pred) if minute_pred is not None else None
                if model:
                    simple=_weighted_mean([x["PTS"] for x in prior])
                    evaluated.append({
                        "season":season,"date":day,"player_id":pid,
                        "predicted_fga":model["expected_fga"],"actual_fga":g["FGA"],
                        "predicted_2pa":model["expected_2pa"],"actual_2pa":g["FGA"]-g["FG3A"],
                        "predicted_3pa":model["expected_3pa"],"actual_3pa":g["FG3A"],
                        "predicted_fta":model["expected_fta"],"actual_fta":g["FTA"],
                        "predicted_points":model["expected_points"],
                        "simple_points":simple,"actual_points":g["PTS"]})
            history.append(g)
    holdout=[x for x in evaluated if x["season"]==TEST_SEASON]
    earlier=[x for x in evaluated if x["season"]!=TEST_SEASON]
    stats=metrics(holdout)
    return {
        "status":"ARCHIVED_SHOT_OPPORTUNITY_HOLDOUT" if stats["observations"]>=100 else "INSUFFICIENT_SHOT_HOLDOUT",
        "seasons":list(SEASONS),"holdout_season":TEST_SEASON,
        "archive_valid_player_games":len(records),
        "earlier_seasons":metrics(earlier),"holdout":stats,
        "live_model_unchanged":True,"production_adjustment_applied":False,
        "injury_usage_change_applied":False,
        "shot_location_detail":"TWO_POINT_VERSUS_THREE_POINT_ONLY",
        "limitations":[
            "2PA is reconstructed as FGA-3PA; no rim/midrange/corner data.",
            "2PM is FGM-3PM and points are reconstructed as 2*2PM+3*3PM+FTM.",
            "Free throws are projected separately; points are not just field goals.",
            "Only earlier same-player same-team same-season games determine shot mix and rates.",
            "2025-26 entire season is held out from any research candidate tuning.",
            "Bench status, DNP, and true player-tracking shot opportunities are unavailable.",
            "No direct impact on current NBA AI predictions or betting decisions."
        ]}


def main():
    records,rejected=load_history()
    report=evaluate(records)
    report["generated_at"]=datetime.now(timezone.utc).isoformat()
    report["quality_rejections"]=rejected
    OUTPUT.write_text(__import__("json").dumps(report,indent=2)+"\n")
    print("SHOT PROFILE RESEARCH",__import__("json").dumps({
        "status":report["status"],"archive_valid_player_games":report["archive_valid_player_games"],
        "holdout":report["holdout"],"quality_rejections":rejected}),flush=True)


if __name__=="__main__":main()

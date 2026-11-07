"""Research-only defender-aware POINTS holdout on real completed player box scores.

Two independently sourced 2025-26 archives:
  1. player game logs: actual player points and historical 2P/3P/FT profile
  2. player-defender game matchups: defender shot-contest history + team identity

Forecasts use STRICTLY EARLIER event dates. Historical opponent defender exposure
is estimated from earlier completed rotations, not a confirmed assignment.
Same-game defense and actual player points are NEVER model inputs.
No odds or simulated hit probabilities. No production model changes.
"""
import collections
import datetime as dt
import io
import json
import math
import pathlib
import urllib.request
from statistics import mean

try:
    from .defender_matchup_v3 import ROOT
    from .shot_profile_research import predict_points
    from .import_archived_defender_matchups import PARQUET_URL,archive_minutes
except ImportError:
    from defender_matchup_v3 import ROOT
    from shot_profile_research import predict_points
    from import_archived_defender_matchups import PARQUET_URL,archive_minutes

MATCHUP_FILE=ROOT/"data/nba/research/matchups2025.parquet"
PLAYER_FILE=ROOT/"data/nba/research/game_logs_2025-26.parquet"
PLAYER_URL="https://huggingface.co/datasets/Sangameshsb/nba-game-logs/resolve/main/game_logs/game_logs_2025-26.parquet"
REPORT=ROOT/"docs/defender_v3_points_holdout.json"
SHRINK_2PA=300.
SHRINK_3PA=220.
# Fixed research parameters: not tuned on holdout games.
SCALE=.65
MAX_DELTA_POINTS=2.0
MIN_DEF_2PA=25
MIN_TEAM_DEFENDERS=3
MIN_TEST_DATES=20
TEST_FRACTION=.20
COLS=("player_id","game_id","game_date","team","opponent","minutes",
      "pts","fgm","fga","fg3m","fg3a","ftm","fta")
ALIASES={"BRK":"BKN","GS":"GSW","GOL":"GSW","PHO":"PHX","SA":"SAS",
         "SAN":"SAS","NY":"NYK","NO":"NOP","NOR":"NOP","UTH":"UTA"}
def team(x):
    key=str(x or "").strip().upper()
    return ALIASES.get(key,key)
def uid(x):
    value=str(x or "").strip()
    if value.endswith(".0") and value[:-2].isdigit():value=value[:-2]
    return value.lstrip("0") or "0"
def number(x):
    try:
        n=float(x)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):return None


def load_player_games(table):
    missing=set(COLS)-set(table.column_names)
    if missing:raise ValueError("Missing actual box score fields: "+str(sorted(missing)))
    by_key={}
    for row in table.select(COLS).to_pylist():
        try:
            date=dt.date.fromisoformat(str(row["game_date"])[:10])
            if not dt.date(2025,10,1)<=date<=dt.date(2026,7,1):continue
            p=uid(row["player_id"]);gid=uid(row["game_id"])
            tm=team(row["team"]);opp=team(row["opponent"])
            if not p.isdigit() or not gid.isdigit() or tm==opp or not tm or not opp:continue
            vals={col:number(row[field]) for col,field in (("MIN","minutes"),
                ("PTS","pts"),("FGM","fgm"),("FGA","fga"),("FG3M","fg3m"),
                ("FG3A","fg3a"),("FTM","ftm"),("FTA","fta"))}
            if any(x is None for x in vals.values()) or not 0<vals["MIN"]<=60:continue
            if vals["FGM"]>vals["FGA"] or vals["FG3M"]>vals["FGM"] or vals["FG3A"]>vals["FGA"]:continue
            if vals["FG3M"]>vals["FG3A"] or vals["FTM"]>vals["FTA"]:continue
            if abs(vals["PTS"]-(2*vals["FGM"]+vals["FG3M"]+vals["FTM"]))>.01:continue
            key=(gid,p)
            if key in by_key:raise ValueError("Duplicate player-game box score")
            by_key[key]={"date":date.isoformat(),"id":p,"game_id":gid,
                        "team":tm,"opponent":opp,**vals}
        except (TypeError,ValueError,KeyError):continue
    if not by_key:raise ValueError("No valid 2025-26 player box scores")
    return sorted(by_key.values(),key=lambda r:(r["date"],r["game_id"],r["id"]))


def load_defender_games(table,box_games):
    required={"game_id","person_id","matchups_person_id","team_tricode",
      "matchup_minutes","partial_possessions","matchup_field_goals_attempted",
      "matchup_field_goals_made","matchup_three_pointers_attempted",
      "matchup_three_pointers_made","_season","_season_type"}
    if required-set(table.column_names):raise ValueError("Missing split-defender fields")
    identity={(g["game_id"],g["id"]):(g["date"],g["team"]) for g in box_games}
    selected=table.select(sorted(required))
    grouped={}
    failed=collections.Counter()
    for r in selected.to_pylist():
        try:
            if r["_season"]!=2025 or r["_season_type"]!="rg":continue
            gid=uid(r["game_id"]);off=uid(r["matchups_person_id"]);def_id=uid(r["person_id"])
            defender_ident=identity.get((gid,def_id))
            offense_ident=identity.get((gid,off))
            if not defender_ident or not offense_ident:
                failed["missing_boxscore_identity"]+=1;continue
            day,def_team=defender_ident
            if offense_ident[0]!=day or offense_ident[1]==def_team or team(r["team_tricode"])!=def_team:
                failed["team_or_day_mismatch"]+=1;continue
            mins=archive_minutes(r["matchup_minutes"])
            values=[number(r[x]) for x in ("partial_possessions","matchup_field_goals_attempted",
                         "matchup_field_goals_made","matchup_three_pointers_attempted",
                         "matchup_three_pointers_made")]
            if mins is None or mins<=0 or None in values:continue
            possessions,fga,fgm,three_a,three_m=values
            two_a=fga-three_a;two_m=fgm-three_m
            if (fga>possessions or fgm>fga or three_m>three_a or
                two_a<0 or two_m<0 or two_m>two_a):continue
            key=(day,gid,def_id,off)
            agg=grouped.setdefault(key,{"date":day,"game_id":gid,
              "def_id":def_id,"off_id":off,"def_team":def_team,
              "two_a":0.,"two_m":0.,"three_a":0.,"three_m":0.})
            for name,value in zip(("two_a","two_m","three_a","three_m"),
                                  (two_a,two_m,three_a,three_m)):
                agg[name]+=value
        except (ValueError,TypeError,KeyError):continue
    return sorted(grouped.values(),key=lambda r:(r["date"],r["game_id"],r["off_id"],r["def_id"])),dict(failed)


def defender_adjustment(baseline,defenders,league2=.52,league3=.35):
    """Minutes-weighted defender impact; no defender minutes means NO adjustment.

    Defender shooting allowed is stabilized toward league reference rates,
    then compared with league, rather than treating all players as identical.
    This is a *scenario*, not measured assignment probability.
    """
    if not defenders or len(defenders)<MIN_TEAM_DEFENDERS:return baseline["expected_points"],None
    weighted=[]
    for minutes,history in defenders:
        if minutes<=0 or history["two_a"]<MIN_DEF_2PA:continue
        p2=(history["two_m"]+SHRINK_2PA*league2)/(history["two_a"]+SHRINK_2PA)
        p3=(history["three_m"]+SHRINK_3PA*league3)/(history["three_a"]+SHRINK_3PA)
        weighted.append((minutes,p2-league2,p3-league3))
    if len(weighted)<MIN_TEAM_DEFENDERS:return baseline["expected_points"],None
    weight=sum(item[0] for item in weighted)
    two_diff=sum(m*d2 for m,d2,_ in weighted)/weight
    three_diff=sum(m*d3 for m,_,d3 in weighted)/weight
    # Keep field-goal opportunity and free throw assumptions from the baseline
    # to isolate measured effect of the defender-specific efficiency inputs.
    delta=SCALE*(2*baseline["expected_2pa"]*two_diff+
                 3*baseline["expected_3pa"]*three_diff)
    delta=max(-MAX_DELTA_POINTS,min(MAX_DELTA_POINTS,delta))
    return round(max(0,baseline["expected_points"]+delta),3),round(delta,3)


def head_to_head_adjustment(baseline,defenders,pair_history,off_id):
    """Individual history only, strictly earlier than target date.

    Each defender remains a candidate, not a confirmed assignment. Historical
    matchup possessions modulate exposure but never override recent minutes.
    The adjustment is relative to the offensive player's own prior 2P/3P
    baseline, shrunk toward no effect and capped at +/-2 scoring points.
    """
    if len(defenders)<MIN_TEAM_DEFENDERS:return baseline["expected_points"],None,0
    two=three=weight=0.
    covered=0
    for defender_id,mins,previous in defenders:
        if mins<=0:continue
        pair=pair_history.get((str(off_id),str(defender_id)))
        if not pair or pair["poss"]<10:continue
        pa2=pair["two_a"];pa3=pair["three_a"]
        if pa2+pa3<3:continue
        b2=baseline["expected_2p_pct"];b3=baseline["expected_3p_pct"]
        effect2=(pair["two_m"]+60*b2)/(pa2+60)-b2
        effect3=(pair["three_m"]+50*b3)/(pa3+50)-b3
        # Past possessions increase relevance only modestly; the rest of the
        # opponent rotation is a neutral unobserved matchup, not secretly zero.
        exposure=min(2.,1+pair["poss"]/80.)
        effective_weight=mins*exposure
        two+=effective_weight*effect2
        three+=effective_weight*effect3
        covered+=1
    # Include ALL projected rotation minutes in denominator, so merely having
    # one observed historical pairing cannot imply 100% coverage.
    rotation_minutes=sum(max(0,mins) for _,mins,_ in defenders)
    if covered==0 or rotation_minutes<=0:return baseline["expected_points"],None,0
    shift=SCALE*(2*baseline["expected_2pa"]*two/rotation_minutes+
                 3*baseline["expected_3pa"]*three/rotation_minutes)
    shift=max(-MAX_DELTA_POINTS,min(MAX_DELTA_POINTS,shift))
    return round(max(0,baseline["expected_points"]+shift),3),round(shift,3),covered


def evaluate(box_games,def_rows):
    dates=sorted({x["date"] for x in box_games})
    out={"status":"INSUFFICIENT_SAME_GAME_POINTS_SAMPLE",
         "method":"2025-26 heldout player game dates; strict earlier-date rolling histories",
         "models_compared":"HISTORICAL_SHOT_OPPORTUNITY_VS_MINUTES_WEIGHTED_DEFENDER_SCENARIO",
         "defender_assignment":"UNVERIFIED_MINUTES_PROXY_NOT_CONFIRMED",
         "independent_boxscore_target":"ACTUAL_COMPLETED_PLAYER_POINTS",
         "features_use_same_day_results":False,"training_on_holdout":False,
         "is_live_model":False,"validated_for_live_use":False,
         "promotion_gate":"POINTS_HOLDOUT_NOT_PROVEN",
         "dates_total":len(dates),"test_dates":0,"baseline_points_mae":None,
         "defender_points_mae":None,"defender_minus_baseline_mae":None,
         "games_scored":0,"games_with_defender_context":0,
         "games_without_defender_context":0,
         "head_to_head_games_scored":0,"head_to_head_points_mae":None,
         "head_to_head_baseline_points_mae":None,
         "head_to_head_minus_baseline_mae":None,
         "head_to_head_better_on_holdout":None,
         "head_to_head_pair_coverage":0,
         "expected_exposure_source":"PREVIOUS_5_TEAM_GAMES_DEFENDER_MINUTES",
         "not_a_sportsbook_prop_backtest":True}
    if len(dates)<MIN_TEST_DATES+20:return out
    boundary=dates[int(len(dates)*(1-TEST_FRACTION))]
    out["test_dates"]=sum(d>=boundary for d in dates)
    if out["test_dates"]<MIN_TEST_DATES:return out

    # Build date-sorted updates, freezing today's predictions before ingesting
    # either today's player box scores or today's defensive tracking rows.
    per_day=collections.defaultdict(list);def_day=collections.defaultdict(list)
    for r in box_games:per_day[r["date"]].append(r)
    for r in def_rows:def_day[r["date"]].append(r)
    histories=collections.defaultdict(list)
    team_rotation=collections.defaultdict(lambda:collections.defaultdict(list))
    defense=collections.defaultdict(lambda:{"two_a":0.,"two_m":0.,
                                             "three_a":0.,"three_m":0.})
    pair_hist=collections.defaultdict(lambda:{"poss":0.,"two_a":0.,"two_m":0.,
                                               "three_a":0.,"three_m":0.})
    base_error=def_error=0.
    h2h_base_error=h2h_error=0.
    n_with=n_without=h2h_count=h2h_pairs=0
    examples=[]
    for day in dates:
        if day>=boundary:
            for r in per_day[day]:
                hist=histories[r["id"]]
                baseline=predict_points(hist,day,r["team"],None)
                if baseline is None:continue
                baseline_points=baseline["expected_points"]
                prev_team=team_rotation[r["opponent"]]
                defender_weights=[]
                projected_rotation=[]
                for identifier,prior_minutes in prev_team.items():
                    if not prior_minutes:continue
                    # A player who has not appeared in a rotation for 12 days
                    # is not assumed part of the next matchup.
                    if (dt.date.fromisoformat(day)-dt.date.fromisoformat(prior_minutes[-1][0])).days>12:continue
                    recent=[mins for date,mins in prior_minutes[-5:]]
                    def_hist=defense.get(identifier)
                    if def_hist:
                        defender_weights.append((mean(recent),def_hist))
                        projected_rotation.append((identifier,mean(recent),def_hist))
                predicted,adjustment=defender_adjustment(baseline,defender_weights)
                h2h_pred,h2h_shift,h2h_covered=head_to_head_adjustment(
                    baseline,projected_rotation,pair_hist,r["id"])
                if h2h_shift is not None:
                    h2h_count+=1
                    h2h_pairs+=h2h_covered
                    h2h_base_error+=abs(r["PTS"]-baseline_points)
                    h2h_error+=abs(r["PTS"]-h2h_pred)
                # Paired-sample comparison: only score games with valid
                # defender context, and count unavailable context separately.
                if adjustment is None:
                    n_without+=1;continue
                true=r["PTS"]
                base_error+=abs(true-baseline_points)
                def_error+=abs(true-predicted)
                n_with+=1
                if len(examples)<5:examples.append({"date":day,"player_id":r["id"],
                 "opponent":r["opponent"],"baseline_points":baseline_points,
                 "defender_points":predicted,"actual_points":true,
                 "adjustment_points":adjustment})
        # Advance historical state only AFTER all same-day targets are scored.
        for r in per_day[day]:
            histories[r["id"]].append(r)
            team_rotation[r["team"]][r["id"]].append((day,r["MIN"]))
        for r in def_day[day]:
            totals=defense[r["def_id"]]
            for k in ("two_a","two_m","three_a","three_m"):totals[k]+=r[k]
            pair=pair_hist[(r["off_id"],r["def_id"])]
            pair["poss"]+=r["two_a"]+r["three_a"]
            for k in ("two_a","two_m","three_a","three_m"):pair[k]+=r[k]
    out.update(games_with_defender_context=n_with,games_without_defender_context=n_without,
               games_scored=n_with,example_predictions=examples,
               head_to_head_games_scored=h2h_count,
               head_to_head_pair_coverage=h2h_pairs)
    if h2h_count:
        h2h_base=h2h_base_error/h2h_count
        h2h_mae=h2h_error/h2h_count
        out.update(head_to_head_baseline_points_mae=round(h2h_base,4),
                   head_to_head_points_mae=round(h2h_mae,4),
                   head_to_head_minus_baseline_mae=round(h2h_mae-h2h_base,4),
                   head_to_head_better_on_holdout=h2h_mae<h2h_base)
    if n_with:
        base=base_error/n_with;adj=def_error/n_with
        out.update(status="SAME_GAME_DEFENDER_POINTS_HOLDOUT",
             baseline_points_mae=round(base,4),
             defender_points_mae=round(adj,4),
             defender_minus_baseline_mae=round(adj-base,4),
             defender_better_on_holdout=adj<base,
             promotion_gate=("RESEARCH_ONLY_REQUIRES_MULTIPLE_INDEPENDENT_SEASONS_AND_BETTING_LINES"
                if adj<base-.10 else "NO_MEANINGFUL_POINTS_MAE_GAIN"))
    return out


def retrieve(path,url):
    if path.exists():return path
    req=urllib.request.Request(url,headers={"User-Agent":"Sports-Bot-NBA-Research/1.0"})
    with urllib.request.urlopen(req,timeout=40) as resp:
        contents=resp.read(35_000_001)
    if len(contents)>35_000_000 or not(contents.startswith(b"PAR1") and contents.endswith(b"PAR1")):
        raise ValueError("Historical boxscore file is not verified Parquet")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(contents)
    return path


def main():
    out={"status":"DEFENDER_POINTS_HOLDOUT_UNAVAILABLE",
         "is_live_model":False,"validated_for_live_use":False}
    try:
        import pyarrow.parquet as pq
        retrieve(PLAYER_FILE,PLAYER_URL)
        if not MATCHUP_FILE.exists():raise FileNotFoundError("Missing defender matchup archive")
        boxes=load_player_games(pq.read_table(PLAYER_FILE))
        defense,failed=load_defender_games(pq.read_table(MATCHUP_FILE),boxes)
        out.update(evaluate(boxes,defense))
        out.update(source_games=len(boxes),joined_defender_records=len(defense),
                   join_rejections=failed)
    except (OSError,ValueError,TypeError,KeyError,ImportError) as e:
        out.update(error_type=type(e).__name__,error_detail=str(e)[:300])
    out["generated_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
    REPORT.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True),flush=True)


if __name__=="__main__":main()

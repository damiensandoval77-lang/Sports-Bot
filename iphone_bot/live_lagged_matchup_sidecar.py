"""Points-only independent live challenger; never overwrites incumbent AI board.

Model fit uses 2022-24, not outcomes from 2026-27. Current opponent context
uses reciprocal validated completed team boxes only. A missing feature means
NO CHALLENGER, never a silently fabricated pick. Authentic PrizePicks lines
are consumed only if independently verified and earlier than the game tipoff.
"""
import json,math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo
import numpy as np

try:
    from .lagged_matchup_training import make_rows,COLS,TRAIN
    from .expanded_matchup_research import build_team_games,defense_factor
    from .offensive_involvement_holdout import predict
    from .points_hit_probability import estimate as estimate_hit_probability
except ImportError:
    from lagged_matchup_training import make_rows,COLS,TRAIN
    from expanded_matchup_research import build_team_games,defense_factor
    from offensive_involvement_holdout import predict
    from points_hit_probability import estimate as estimate_hit_probability

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/lagged_matchup_live_points.json"
STATUS="LIVE_POINTS_CHALLENGER_UNCALIBRATED"
ET=ZoneInfo("America/New_York")

def stamp(x):
    try:
        z=datetime.fromisoformat(str(x).replace("Z","+00:00"))
        if z.tzinfo is None:raise ValueError
        return z.astimezone(timezone.utc)
    except (TypeError,ValueError) as e:
        raise ValueError("Timezone-aware capture/fixture required") from e

def current_games(local,validated_shooting):
    """Attach only exact crosschecked current stats; reject identity conflicts."""
    indexed={}
    bad=set()
    for raw in validated_shooting:
        pid=str(raw.get("player_id") or raw.get("id") or "")
        team=str(raw.get("team") or "").upper()
        day=str(raw.get("game_date") or raw.get("date") or "")[:10]
        key=(pid,team,day)
        expected=("pts","reb","ast","minutes","fga","fta","tov","oreb")
        try:
            vals={k:float(raw[k]) for k in expected}
        except (ValueError,TypeError,KeyError):continue
        if not pid.isdigit() or not all(math.isfinite(v) and v>=0 for v in vals.values()):
            continue
        if not (0<vals["minutes"]<=60):continue
        if key in indexed and indexed[key]!=vals:bad.add(key)
        indexed[key]=vals
    rows=[]
    coverage=defaultdict(int)
    for r in local:
        key=(str(r.get("id")),str(r.get("team") or "").upper(),str(r.get("date") or "")[:10])
        v=indexed.get(key)
        if key in bad or v is None:
            coverage["NO_MATCHED_COMPLETE_BOX"]+=1;continue
        if any(abs(float(r.get(local_key,-999))-v[remote_key])>0.01
               for local_key,remote_key in (("PTS","pts"),("REB","reb"),("AST","ast"))):
            coverage["BOX_SCORE_DISAGREEMENT"]+=1;continue
        if abs(float(r.get("MIN",-999))-v["minutes"])>2.5:
            coverage["MINUTES_DISAGREEMENT"]+=1;continue
        # CSV minutes are rounded; the crosschecked source can reveal a
        # subminute cameo. All model inputs require at least one real minute
        # (the CSV importer, CSV recovery and predict() share this boundary).
        # Exclude just that row rather than poisoning otherwise sufficient
        # history, and never round the observed duration up to qualify it.
        if v["minutes"]<1:
            coverage["BELOW_MODEL_MINIMUM_MINUTES"]+=1;continue
        enriched={**r,"season":"2026-27","FGA":v["fga"],
                  "FTA":v["fta"],"TOV":v["tov"],"OREB":v["oreb"],
                  "MIN":v["minutes"],"id":key[0]}
        rows.append(enriched)
        coverage["MATCHED"]+=1
    return rows,dict(coverage)

def build_features(history,team,opponent,day,team_games,*,neutral_defense_on_missing=False):
    recent=sorted((r for r in history if r.get("team")==team and r.get("date","")<day),
                  key=lambda r:r["date"])
    if len({r["date"] for r in recent})!=len(recent):
        return None,"DUPLICATE_PRIOR_PLAYER_GAME"
    base=predict(recent)
    if base is None:return None,"INSUFFICIENT_PLAYER_OPPORTUNITY_HISTORY"
    opp=defense_factor(team_games,team,opponent,day)
    if opp["status"]!="PRIOR_RECIPROCAL_TEAM_BOX_CONTEXT":
        if not neutral_defense_on_missing:
            return None,"INSUFFICIENT_PRIOR_OPPONENT_PACE_DEFENSE"
        # Neutral is a declared missing-feature fallback, NOT measured defense.
        # The trained model may still estimate a descriptive baseline from verified
        # prior player history, but no matchup-adjusted hit chance can be claimed.
        opp={"pace_factor":1.0,"defense_factor":1.0}
        defense_unavailable=True
    else:
        defense_unavailable=False
    volume=sum(r["FGA"]+.44*r["FTA"]+r["TOV"] for r in recent)
    if volume<=0:return None,"INVALID_OPPORTUNITY_DENOMINATOR"
    recent10=recent[-10:]
    f={"minutes_forecast":base["minutes_projection"],
      "involvement_per_min":base["involvement_proxy"],
      "last3_points":mean(r["PTS"] for r in recent[-3:]),
      "last10_points":mean(r["PTS"] for r in recent10),
      "prior_points_per_involvement":sum(r["PTS"] for r in recent)/volume,
      "recent_fga_per_min":mean(r["FGA"]/r["MIN"] for r in recent10),
      "recent_fta_per_min":mean(r["FTA"]/r["MIN"] for r in recent10),
      "recent_turnover_per_min":mean(r["TOV"]/r["MIN"] for r in recent10),
      "opponent_pace_factor":opp["pace_factor"],
      "opponent_defense_factor":opp["defense_factor"],
      "last3_minutes":mean(r["MIN"] for r in recent[-3:]),
      "last10_minutes":mean(r["MIN"] for r in recent10),
      "history_count":min(82,len(recent))}
    f["opponent_context_unavailable"]=defense_unavailable
    if not all(math.isfinite(float(f[x])) for x in COLS):
        return None,"NONFINITE_LAGGED_FEATURE"
    return f,None

def standard_points_offers(picks):
    """One verified two-sided standard PrizePicks points line per player/game.

    The upstream market feed contains demon and goblin alternatives at
    different thresholds. Those must NEVER be used for the new AI's standard
    comparison or probability. Ambiguous distinct standard thresholds fail
    closed; do not pick the highest, lowest or first arbitrary line.
    """
    grouped=defaultdict(list)
    rejected=defaultdict(int)
    for p in picks:
        if p.get("stat")!="Points":
            continue
        if p.get("pickem_tier")!="standard":
            rejected["NON_STANDARD_POINTS_TIER"]+=1
            continue
        if p.get("direction") not in ("More","Less"):
            rejected["INVALID_STANDARD_SIDE"]+=1
            continue
        try:
            line=float(p["line"])
        except (ValueError,TypeError,KeyError):
            rejected["INVALID_STANDARD_LINE"]+=1
            continue
        if not math.isfinite(line) or line<0 or line>100:
            rejected["INVALID_STANDARD_LINE"]+=1
            continue
        key=(str(p.get("player","")).casefold(),str(p.get("team","")),
             str(p.get("game","")),str(p.get("start","")))
        grouped[key].append(p)
    selected=[]
    for group in grouped.values():
        unique_lines={float(p["line"]) for p in group}
        if len(unique_lines)!=1:
            rejected["CONFLICTING_STANDARD_LINES"]+=len(group)
            continue
        sides={p["direction"] for p in group}
        if sides!={"More","Less"}:
            rejected["INCOMPLETE_STANDARD_TWO_SIDED_LINE"]+=len(group)
            continue
        # Both directions quote the same standard number. One entry suffices
        # for the projection and its independently calculated over/under odds.
        most_recent=max(group,key=lambda p:str(p.get("market_updated") or ""))
        selected.append({**most_recent,"pickem_tier":"standard",
                         "standard_line_two_sided_verified":True})
    return selected,dict(rejected)


def forecast(records,offers,model_pack,*,now=None):
    now=now or datetime.now(timezone.utc)
    if model_pack.get("research_only") is not True or model_pack.get("production_modified") is not False:
        raise ValueError("Unverified model provenance")
    if tuple(model_pack.get("columns") or ())!=tuple(COLS) or tuple(model_pack.get("training_seasons") or ())!=tuple(TRAIN):
        raise ValueError("Unexpected saved model version")
    if offers.get("source")!="AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS" or offers.get("status")!="FRESH_AUTHENTIC_PRIZEPICKS_LINES" or offers.get("is_live") is not True:
        raise ValueError("No currently verified PrizePicks line source")
    updated=stamp(offers["updated_at"])
    if updated>now or (now-updated).total_seconds()>6*3600:
        raise ValueError("Stale PrizePicks feed")
    by_id=defaultdict(list)
    for x in records:by_id[str(x["id"])].append(x)
    roster=defaultdict(set)
    for x in records:
        roster[str(x.get("player","")).casefold()].add((str(x["id"]),x["team"]))
    games=build_team_games(records,season="2026-27")
    out={}
    eligible,standard_rejections=standard_points_offers(offers["picks"])
    excluded=defaultdict(int,standard_rejections)
    for p in eligible:
        player=str(p.get("player","")).casefold()
        matches=roster.get(player,set())
        if len(matches)!=1:
            excluded["PLAYER_IDENTITY_NOT_UNIQUE"]+=1;continue
        pid,team=next(iter(matches))
        matchup=str(p.get("game") or "").split(" @ ")
        if len(matchup)!=2:
            excluded["INVALID_MATCHUP"]+=1;continue
        team_names={"Atlanta Hawks":"ATL","Boston Celtics":"BOS","Brooklyn Nets":"BKN",
        "Charlotte Hornets":"CHA","Chicago Bulls":"CHI","Cleveland Cavaliers":"CLE",
        "Dallas Mavericks":"DAL","Denver Nuggets":"DEN","Detroit Pistons":"DET",
        "Golden State Warriors":"GSW","Houston Rockets":"HOU","Indiana Pacers":"IND",
        "Los Angeles Clippers":"LAC","LA Clippers":"LAC","Los Angeles Lakers":"LAL",
        "Memphis Grizzlies":"MEM","Miami Heat":"MIA","Milwaukee Bucks":"MIL",
        "Minnesota Timberwolves":"MIN","New Orleans Pelicans":"NOP",
        "New York Knicks":"NYK","Oklahoma City Thunder":"OKC","Orlando Magic":"ORL",
        "Philadelphia 76ers":"PHI","Phoenix Suns":"PHX","Portland Trail Blazers":"POR",
        "Sacramento Kings":"SAC","San Antonio Spurs":"SAS","Toronto Raptors":"TOR",
        "Utah Jazz":"UTA","Washington Wizards":"WAS"}
        sides=[team_names.get(v) for v in matchup]
        if None in sides or team not in sides:
            excluded["TEAM_MISMATCH"]+=1;continue
        opp=next(x for x in sides if x!=team)
        tip=stamp(p.get("start"));quote_time=stamp(p.get("market_updated"))
        if not (now<tip and quote_time<=now and quote_time<tip):
            excluded["NOT_CURRENT_PREGAME"]+=1;continue
        day=tip.astimezone(ET).date().isoformat()
        f,reason=build_features(by_id[pid],team,opp,day,games)
        if reason:
            excluded[reason]+=1;continue
        pred=float(model_pack["model"].predict(np.array([[f[k] for k in COLS]],dtype=float))[0])
        if not math.isfinite(pred) or pred<0 or pred>100:
            excluded["INVALID_FORECAST"]+=1;continue
        key=(pid,team,p["game"],p["start"],p["line"])
        reference=model_pack.get("probability_reference")
        probability=(estimate_hit_probability(pred,float(p["line"]),reference,key)
                     if isinstance(reference,dict) else None)
        item=out.setdefault(key,{"player":p["player"],"player_id":pid,"team":team,
            "opponent":opp,"game":p["game"],"start":p["start"],"stat":"PTS",
            "line":p["line"],"market_updated":p["market_updated"],
            "pickem_tier":"standard","standard_line_two_sided_verified":True,
            "projection":round(pred,3),"captured_at":now.isoformat(),
            "prediction_model":"TRAINED_2022_24_LAGGED_MATCHUP_POINTS_CHALLENGER",
            "calibrated_probability":None,"simulated_hit_rate":None,
            "estimated_hit_chance":probability,
            "official_usage_applied":False,"verified_injury_applied":False,
            "position_defense_applied":False,
            "source_prior_games":sum(x["date"]<day and x["team"]==team for x in by_id[pid]),
            "real_prizepicks_line":True,"research_only":True,
            "new_model_direction_unvalidated":True,"production_replaced":False})
        if item["projection"]!=round(pred,3):
            raise ValueError("Conflicting same-identity projection")
    return {"status":STATUS,"generated_at":now.isoformat(),
      "model":"TRAINED_2022_24_LAGGED_MATCHUP_POINTS_CHALLENGER",
      "points_only":True,"published_projections":len(out),
      "predictions":list(out.values()),"excluded":dict(excluded),
      "source":"INDEPENDENT_VERIFIED_PRIZEPICKS_LINES",
      "live_model_replaced":False,"probabilities_validated":False,
      "historical_hit_probability_model":"2024_25_OUT_OF_TRAINING_RESIDUALS",
      "market_line_policy":"STANDARD_ONLY_BOTH_SIDES_VERIFIED_NO_ALTERNATES",
      "production_grades_modified":False}

def main():
    import os
    import joblib, requests, pandas as pd
    from io import BytesIO
    model_path=Path(os.environ.get("LAGGED_MODEL_PATH",
        str(ROOT/"models/nba/research/lagged_matchup_2022_24.joblib")))
    current_path=ROOT/"data/nba/current/current_games.json"
    offer_path=ROOT/"docs/prizepicks_model_input.json"
    if not all(x.exists() for x in (model_path,current_path,offer_path)):
        raise RuntimeError("Missing model, verified current games or authentic line file")
    url="https://huggingface.co/datasets/cbratkovics/nba-game-logs/resolve/main/game_logs/game_logs_2026-27.parquet"
    r=requests.get(url,timeout=(12,45),headers={"User-Agent":"SportsBot-Research/1.0"})
    r.raise_for_status()
    if len(r.content)>12_000_000:raise ValueError("Unexpectedly large source")
    source=pd.read_parquet(BytesIO(r.content))
    required={"player_id","game_date","team","pts","reb","ast","minutes","fga","fta","tov","oreb"}
    if not required.issubset(source.columns):raise ValueError("No complete shooting opportunity source")
    source=source.rename(columns={"player_id":"id","game_date":"date"})
    source["date"]=pd.to_datetime(source["date"],errors="raise").dt.strftime("%Y-%m-%d")
    source["season"]="2026-27"
    rows,coverage=current_games(json.loads(current_path.read_text()),source.to_dict(orient="records"))
    if len(rows)<1000:raise RuntimeError("Too few crosschecked player-games for opponent pace")
    report=forecast(rows,json.loads(offer_path.read_text()),joblib.load(model_path))
    report["source_coverage"]=coverage
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print("LIVE_MATCHUP_CHALLENGER",json.dumps({"published":report["published_projections"],
        "excluded":report["excluded"],"matched_player_games":coverage.get("MATCHED",0)}),flush=True)

if __name__=="__main__":
    main()

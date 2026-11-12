"""One coherent new AI source for verified standard PTS/REB/AST/PRA lines.

Correlated PRA = PTS+REB+AST, from independently trained PTS/REB/AST
models with 2024-25 paired residual samples. Research estimates are
not calibrated betting probabilities. Existing grades remain unmodified.
"""
import json
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from io import BytesIO
import numpy as np

try:
    from .live_lagged_matchup_sidecar import (ROOT,ET,stamp,current_games,
       build_features,standard_points_offers)
    from .expanded_matchup_research import build_team_games
    from .multimarket_matchup_training import FEATURES,COLS,TRAIN
    from .multimarket_probability import simulate,METHOD
    from .new_ai_injury_context import injury_adjustment
except ImportError:
    from live_lagged_matchup_sidecar import (ROOT,ET,stamp,current_games,
       build_features,standard_points_offers)
    from expanded_matchup_research import build_team_games
    from multimarket_matchup_training import FEATURES,COLS,TRAIN
    from multimarket_probability import simulate,METHOD
    from new_ai_injury_context import injury_adjustment

OUTPUT=ROOT/"docs/lagged_matchup_live_all_markets.json"
STATS={"Points":"PTS","Rebounds":"REB","Assists":"AST","Points Rebounds Assists":"PRA"}
TEAM={"Atlanta Hawks":"ATL","Boston Celtics":"BOS","Brooklyn Nets":"BKN",
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

def select_standard(offers):
    """Same verified standard both-side threshold rule for all four markets."""
    selected=[]
    reasons=defaultdict(int)
    for stat in STATS:
        sample=[{**p,"stat":"Points"} for p in offers if p.get("stat")==stat]
        allowed,excluded=standard_points_offers(sample)
        for x in allowed:
            selected.append({**x,"stat":stat})
        for k,v in excluded.items():reasons[k]+=v
    return selected,dict(reasons)

def resolve_current_roster_identity(player, game, roster, latest_team):
    """Match a name to one last-observed team present in this exact fixture.

    Never infer a roster assignment from a sportsbook quote alone. Historical
    traded-team rows are not independent identities for the same player.
    """
    sides=[TEAM.get(x.strip()) for x in str(game or "").split(" @ ")]
    if len(sides)!=2 or None in sides or sides[0]==sides[1]:
        return None,"GAME_TEAM_IDENTITY_MISMATCH"
    candidates=set()
    for pid,team in roster.get(str(player or "").casefold(),set()):
        if team in sides and latest_team.get(pid)==team:
            candidates.add((pid,team))
    if len(candidates)!=1:
        return None,("CURRENT_ROSTER_IDENTITY_NOT_VERIFIED" if not candidates
                     else "PLAYER_IDENTITY_NOT_UNIQUE")
    pid,team=next(iter(candidates))
    return (pid,team,sides[0] if sides[1]==team else sides[1]),None

def feature_vector(history,team,opponent,day,team_context):
    common,reason=build_features(history,team,opponent,day,team_context,
                                 neutral_defense_on_missing=True)
    if reason:return None,reason
    recent=sorted((r for r in history if r.get("team")==team and r.get("date","")<day),
                  key=lambda x:x["date"])
    last10=recent[-10:]
    if any(r.get(s) is None for r in last10 for s in ("REB","AST")):
        return None,"MISSING_REB_AST_PRIOR_HISTORY"
    for stat in ("REB","AST"):
        common[stat+"_L3"]=float(np.mean([r[stat] for r in recent[-3:]]))
        common[stat+"_L10"]=float(np.mean([r[stat] for r in last10]))
        common[stat+"_PER_MIN_L10"]=float(np.mean([r[stat]/r["MIN"] for r in last10]))
    if not all(np.isfinite(float(common[k])) for k in FEATURES):
        return None,"NONFINITE_ALL_MARKET_FEATURES"
    return common,None

def per_game_diagnostics(feed,selected,predictions,blocked):
    """Give each game auditable coverage and exclusion counts, without inventing picks."""
    games=defaultdict(lambda:{"observed_provider_quote_rows":0,"verified_standard_offers":0,
                              "frozen_forecasts":0,"excluded":defaultdict(int)})
    for x in feed.get("picks",[]):
        if x.get("game"):games[x["game"]]["observed_provider_quote_rows"]+=1
    for x in selected:
        if x.get("game"):games[x["game"]]["verified_standard_offers"]+=1
    for x in predictions:
        if x.get("game"):games[x["game"]]["frozen_forecasts"]+=1
    for game,causes in blocked.items():
        for reason,count in causes.items():
            games[game]["excluded"][reason]+=count
    return {game:{**item,"excluded":dict(item["excluded"])} for game,item in sorted(games.items())}

def forecasts(records,feed,pack,now=None,*,injuries=None,news=None,free_watch=None):
    now=now or datetime.now(timezone.utc)
    injuries=injuries or {}
    news=news or {}
    free_watch=free_watch or {}
    if (pack.get("research_only") is not True or pack.get("calibrated") is not False or
        tuple(pack.get("training_seasons") or ())!=tuple(TRAIN) or
        tuple(pack.get("feature_columns") or ())!=tuple(FEATURES)):
        raise ValueError("Unverified multimarket artifact")
    residuals=np.asarray(pack.get("validation_residual_triplets"),dtype=float)
    if residuals.ndim!=2 or residuals.shape[1]!=3 or len(residuals)<1000 or not np.isfinite(residuals).all():
        raise ValueError("No validated joint residual pool")
    if (feed.get("source")!="AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS" or
        feed.get("status")!="FRESH_AUTHENTIC_PRIZEPICKS_LINES" or feed.get("is_live") is not True):
        raise ValueError("Verified standard live lines unavailable")
    captured=stamp(feed["updated_at"])
    if captured>now or (now-captured).total_seconds()>6*3600:
        raise ValueError("PrizePicks feed stale")
    selected,excluded=select_standard(feed.get("picks",[]))
    rejected=defaultdict(int,excluded)
    blocked_by_game=defaultdict(lambda:defaultdict(int))
    def block(item,reason):
        rejected[reason]+=1
        blocked_by_game[str(item.get("game") or "UNKNOWN")][reason]+=1
    by_id=defaultdict(list)
    roster=defaultdict(set)
    latest_by_id={}
    for r in records:
        pid=str(r["id"])
        by_id[pid].append(r)
        roster[str(r.get("player","")).casefold()].add((pid,r["team"]))
        # Resolve traded histories using the latest actual player-game date,
        # not a historical team from the same season or a guessed quote team.
        day_seen=str(r.get("date") or "")
        if day_seen and (pid not in latest_by_id or day_seen>latest_by_id[pid][0]):
            latest_by_id[pid]=(day_seen,r["team"])
        elif pid in latest_by_id and day_seen==latest_by_id[pid][0] and r["team"]!=latest_by_id[pid][1]:
            latest_by_id[pid]=(day_seen,None)
    latest_team={pid:team for pid,(_,team) in latest_by_id.items()}
    single_source_teams={r["team"] for r in records
                         if r.get("history_source_confidence")}
    defense=build_team_games(records,season="2026-27")
    cache={}
    feature_flags={}
    predictions=[]
    for item in selected:
        identity,reason=resolve_current_roster_identity(
            item.get("player"),item.get("game"),roster,latest_team)
        if reason:
            block(item,reason);continue
        pid,team,opponent=identity
        tip=stamp(item["start"]);observed=stamp(item["market_updated"])
        if not(now<tip and observed<=now and observed<tip):
            block(item,"LATE_OR_INVALID_MARKET");continue
        day=tip.astimezone(ET).date().isoformat()
        key=(pid,team,opponent,day)
        if key not in cache:
            vec,reason=feature_vector(by_id[pid],team,opponent,day,defense)
            if reason:cache[key]=(None,reason)
            else:
                feature_flags[key]={"opponent_context_unavailable":vec.get("opponent_context_unavailable",False)}
                x=np.array([[vec[k] for k in FEATURES]],dtype=float)
                xp=np.array([[vec[k] for k in COLS]],dtype=float)
                model=pack["models"]
                pred={"PTS":max(0.,float(model["PTS"].predict(xp)[0])),
                      "REB":max(0.,float(model["REB"].predict(x)[0])),
                      "AST":max(0.,float(model["AST"].predict(x)[0]))}
                cache[key]=(pred,None)
        p,reason=cache[key]
        if reason:block(item,reason);continue
        injury=injury_adjustment(p,pid,team,opponent,day,item["start"],now,
                                 injuries,news,records,free_watch=free_watch)
        if injury["status"]=="PLAYER_REPORTED_OUT_SUPPRESS_ALL_MARKETS":
            block(item,"REPORTED_OUT_PLAYER_SUPPRESSED")
            continue
        if injury["status"]=="INJURY_MATCHUP_DATA_INSUFFICIENT":
            block(item,"INJURY_AFFECTED_PROJECTION_WITHHELD")
            continue
        p={k:float(v)*injury["factor"] for k,v in p.items()}
        stat=STATS[item["stat"]]
        identity=(pid,team,item["game"],tip.isoformat(),stat,item["line"],
                  injury["status"],tuple((v["player_id"],v["reported_at"]) for v in injury["affected"]))
        simulation=simulate(p,item["line"],stat,residuals,identity)
        if simulation["method"]!=METHOD:raise ValueError("Unknown probability method")
        predictions.append({"player":item["player"],"player_id":pid,"team":team,
         "opponent":opponent,"game":item["game"],"start":item["start"],
         "stat":stat,"line":float(item["line"]),
         "projection":simulation["projection"],
         "components":simulation["component_projections"],
         "market_updated":item["market_updated"],
         "captured_at":now.isoformat(),
         "pickem_tier":"standard","standard_line_two_sided_verified":True,
         "estimated_hit_chance":simulation,
         "injury_reprojection_status":injury["status"],
         "injury_context":injury,
         "opponent_context_unavailable":bool((feature_flags.get(key) or {}).get("opponent_context_unavailable")),
        "single_source_history":(
             team in single_source_teams or opponent in single_source_teams),
        "injury_uncertainty_unresolved":injury["status"]=="BASELINE_WITH_UNRESOLVED_INJURY",
         "opponent_adjustment_verified":not bool((feature_flags.get(key) or {}).get("opponent_context_unavailable"))
           and opponent not in single_source_teams,
         "prediction_quality":"NEUTRAL_OPPONENT_CONTEXT_FALLBACK" if (feature_flags.get(key) or {}).get("opponent_context_unavailable") else "VERIFIED_PRIOR_OPPONENT_CONTEXT",
         "injury_adjustment_verified":injury["status"]!="BASELINE_WITH_UNRESOLVED_INJURY",
         "calibrated_probability":None,
         "source_prior_games":sum(r["date"]<day and r["team"]==team for r in by_id[pid]),
         "research_only":True,"production_replaced":False})
    if not predictions:raise RuntimeError("No verified multi-stat comparisons; preserve existing data")
    return {"status":"LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED",
      "generated_at":now.isoformat(),
      "model":"LAGGED_MATCHUP_2022_24_THREE_MODELS_PRA_SUM",
      "market_line_policy":"STANDARD_ONLY_BOTH_SIDES_VERIFIED_NO_ALTERNATES",
      "probability_method":METHOD,"component_consistency":True,
      "correlated_pra_scenarios":True,
      "market_counts":{s:sum(r["stat"]==s for r in predictions) for s in STATS.values()},
      "predictions":predictions,"published_projections":len(predictions),
      "excluded":dict(rejected),
      "game_diagnostics":per_game_diagnostics(feed,selected,predictions,blocked_by_game),
      "calibrated":False,
      "injury_news_processed":news.get("status")=="UNDERDOGNBA_X_AUTHENTICATED_POLL",
      "official_injury_processed":injuries.get("injury_data_verified") is True,
      "official_report_issued_at":injuries.get("report_issued_at") if
          injuries.get("status")=="OFFICIAL_NBA_REPORT_VERIFIED" and
          injuries.get("injury_data_verified") is True else None,
      "free_official_injury_transition_watch":free_watch.get("status")=="FREE_OFFICIAL_NBA_INJURY_MONITOR",
      "production_replaced":False,"existing_grades_modified":False}

def main():
    import joblib,requests,pandas as pd
    url="https://huggingface.co/datasets/cbratkovics/nba-game-logs/resolve/main/game_logs/game_logs_2026-27.parquet"
    model=joblib.load(ROOT/"models/nba/research/lagged_matchup_all_markets.joblib")
    form=json.loads((ROOT/"data/nba/current/current_games.json").read_text())
    feed=json.loads((ROOT/"docs/prizepicks_model_input.json").read_text())
    r=requests.get(url,timeout=(12,45),headers={"User-Agent":"SportsBot-Multimarket-Research/1.0"})
    r.raise_for_status()
    if len(r.content)>12_000_000:raise ValueError("Unexpected shooting source size")
    data=pd.read_parquet(BytesIO(r.content))
    need={"player_id","game_date","team","pts","reb","ast","minutes","fga","fta","tov","oreb"}
    if not need.issubset(data.columns):raise ValueError("Incomplete current game data")
    data=data.rename(columns={"player_id":"id","game_date":"date"})
    data["date"]=pd.to_datetime(data["date"],errors="raise").dt.strftime("%Y-%m-%d")
    second_source=data.to_dict(orient="records")
    checked,coverage=current_games(form,second_source)
    # The already-downloaded public player-game CSV includes full observed
    # opportunity counts. Recover only absent (never contradictory) parquet
    # identities after validating exact points and rebound arithmetic.
    try:
        try:
            from .recover_csv_opportunities import recover as recover_csv
        except ImportError:
            from recover_csv_opportunities import recover as recover_csv
        checked,coverage["csv_opportunity_recovery"]=recover_csv(form,checked,second_source)
    except Exception as exc:
        coverage["csv_opportunity_recovery"]={
            "status":"CSV_RECOVERY_ERROR","detail":type(exc).__name__,"recovered":0}
    if len(checked)<1000:raise RuntimeError("Insufficient crosschecked player-games")
    injury_file=ROOT/"docs/injury_context.json"
    news_file=ROOT/"docs/underdog_nba_injury_alerts.json"
    free_file=ROOT/"docs/free_nba_injury_watch.json"
    injuries=json.loads(injury_file.read_text()) if injury_file.exists() else {}
    news=json.loads(news_file.read_text()) if news_file.exists() else {}
    free_watch=json.loads(free_file.read_text()) if free_file.exists() else {}
    result=forecasts(checked,feed,model,injuries=injuries,news=news,free_watch=free_watch)
    result["source_coverage"]=coverage
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print("NEW_ALL_MARKETS",json.dumps({"total":result["published_projections"],
          "markets":result["market_counts"],"excluded":result["excluded"]}),flush=True)

if __name__=="__main__":main()

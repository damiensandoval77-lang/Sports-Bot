"""Experimental trained-model comparisons with VERIFIED current NBA market identities.

No claim of calibrated betting odds, EV, injury adjustments or PrizePicks lines.
Only show upcoming two-sided sportsbook markets where the player roster team
matches one of the game's teams. Training feature gaps are flagged.
"""
import json
import os
import re
import unicodedata
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import joblib
import numpy as np
import pandas as pd
from matchup_context import team_allowances, defense_context, minutes_context
from defense_training import COLS
from experimental_probability import probability_sides, METHOD
from sportsbook_consensus import consensus_markets
from hypothetical_ev import hypothetical_quote_analysis
from combined_projection import combine_projections
from projection_explanation import explain_projection
from research_context import minutes_estimate,positional_allowance,teammate_on_off,injury_minutes_research,minutes_walkforward_backtest
from minutes_model_v2 import forecast as minutes_v2_forecast,backtest as minutes_v2_backtest
from shot_profile_research import predict_attempts as shot_attempt_profile

ROOT=Path(__file__).resolve().parents[1]
GAMES=ROOT/"data/nba/current/current_games.json"
FORM=ROOT/"docs/current_form.json"
ODDS=ROOT/"docs"/os.environ.get("NBA_AI_ODDS_INPUT","data.json")
MODELS=ROOT/"models/nba/provisional"
OUTPUT=ROOT/"docs/ai_comparisons.json"
INJURIES=ROOT/"docs/injury_context.json"
MARKETS={"Points":"PTS","Rebounds":"REB","Assists":"AST","Points Rebounds Assists":"PRA"}
TEAM={
"Atlanta Hawks":"ATL","Boston Celtics":"BOS","Brooklyn Nets":"BKN",
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
def key(x):
    """Match legitimate ASCII sportsbook spellings to accented roster names.

    Keep identity strict: remove accents, spacing and punctuation ONLY.
    Never match substrings or surnames alone; ambiguity fails closed later.
    """
    normalized=unicodedata.normalize("NFKD",str(x or "")).casefold()
    ascii_name="".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]","",ascii_name)
def utc(s):return datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(timezone.utc)
def matchup(x):
    parts=str(x).split(" @ ")
    if len(parts)!=2:return None
    away,home=(TEAM.get(x.strip()) for x in parts)
    if not away or not home or away==home:return None
    return away,home
def predict_features(game_rows,game_date,home):
    by_stat={}
    for stat in ("PTS","REB","AST","MIN","FGA","FG3A","TOV"):
        values=[float(r[stat]) for r in game_rows if r.get(stat) is not None]
        if len(values)<5:return None
        by_stat[stat+"_L5"]=float(np.mean(values[-5:]))
        by_stat[stat+"_L10"]=float(np.mean(values[-10:])) if len(values)>=10 else float(np.mean(values))
        by_stat[stat+"_Season"]=float(pd.Series(values).ewm(span=30,adjust=False).mean().iloc[-1])
    dates=[datetime.fromisoformat(r["date"]).date() for r in game_rows]
    gap=(game_date-dates[-1]).days
    if gap<1 or gap>9:return None
    recent7=sum(0<(game_date-d).days<=7 for d in dates)
    last6=sum(0<(game_date-d).days<=6 for d in dates)
    by_stat.update({"DAYS_REST":min(gap,7),"IS_HOME":int(home),"IS_B2B":int(gap==1),
      "IS_FRESH":int(gap>=3),"GAMES_7D":recent7,"IS_4_IN_6":int(last6>=3)})
    return by_stat

def main():
    now=datetime.now(timezone.utc)
    form=json.loads(FORM.read_text())
    odds=json.loads(ODDS.read_text())
    print("AI sportsbook quote input:",ODDS.name,"outcomes:",len(odds.get("picks",[])),flush=True)
    try:
        injury_feed=json.loads(INJURIES.read_text()) if INJURIES.exists() else {}
        issued=utc(injury_feed["report_issued_at"])
        report_fresh=(injury_feed.get("status") in (
            "OFFICIAL_NBA_REPORT_VERIFIED","THIRD_PARTY_ESPN_INJURY_CONTEXT")
                      and (now-issued).total_seconds()<=18*3600 and issued<=now)
    except (ValueError,TypeError,KeyError):
        injury_feed={}
        report_fresh=False
    # Game-specific official report rows cannot leak into a different fixture.
    # ESPN's generic league listing has no game date and remains nonofficial.
    official_by_event={(str(p["player_id"]),str(p.get("game_date"))):p
                       for p in injury_feed.get("players",[])
                       if p.get("game_date") and p.get("status")!="CONFLICTING_EXTRACT"} if report_fresh else {}
    espn_by_id={str(p["player_id"]):p for p in injury_feed.get("players",[])
                if p.get("provider")=="ESPN_THIRD_PARTY"} if report_fresh else {}

    if form.get("season")!="2026-27":raise ValueError("Not current season")
    form_time=utc(form["updated_at"])
    market_time=utc(odds["updated_at"])
    if (now-form_time).total_seconds()>48*3600 or (now-market_time).total_seconds()>6*3600:
        raise SystemExit("Refusing to publish comparisons from stale player stats or market feed")
    if not odds.get("is_live"):raise ValueError("Sportsbook feed not live")
    roster={}
    for player in form["players"]:
        identity=key(player["player"])
        roster.setdefault(identity,[]).append(player)
    by_id={}
    all_games=json.loads(GAMES.read_text())
    for r in all_games:
        by_id.setdefault(str(r["id"]),{})[r["date"]]=r
    raw_markets={}
    skipped={"not_upcoming":0,"team_mismatch":0,"player_ambiguous":0,"insufficient_stats":0,
             "unsupported_market":0,"stale_market_quote":0}
    for r in odds.get("picks",[]):
        stat=MARKETS.get(r.get("stat"))
        if not stat:
            skipped["unsupported_market"]+=1;continue
        try:
            start=utc(r["start"])
            line=float(r["line"])
            updated=utc(r.get("market_updated") or odds["updated_at"])
        except (TypeError,ValueError,KeyError):
            continue
        if start<=now or start>now.replace(hour=23,minute=59)+pd.Timedelta(days=5):
            skipped["not_upcoming"]+=1;continue
        if updated>now+pd.Timedelta(minutes=10) or (now-updated).total_seconds()>6*3600:
            skipped["stale_market_quote"]+=1;continue
        pair=matchup(r.get("game",""))
        player_id=key(r.get("player",""))
        people=roster.get(player_id,[])
        if len(people)!=1:
            skipped["player_ambiguous"]+=1;continue
        person=people[0]
        if not pair or person["team"] not in pair:
            skipped["team_mismatch"]+=1;continue
        side=r.get("direction")
        if side not in ("More","Less"):continue
        game_date=start.astimezone(ZoneInfo("America/New_York")).date()
        history=sorted(by_id.get(str(person["player_id"]),{}).values(),key=lambda x:x["date"])
        history=[g for g in history if datetime.fromisoformat(g["date"]).date()<game_date]
        if len(history)<5:
            skipped["insufficient_stats"]+=1;continue
        features=predict_features(history,game_date,person["team"]==pair[1])
        if features is None:
            skipped["insufficient_stats"]+=1;continue
        market_key=(person["player_id"],stat,line,r.get("source",""),r["start"])
        market=raw_markets.setdefault(market_key,{"player":person["player"],"player_id":str(person["player_id"]),"team":person["team"],
           "stat":stat,"line":line,"sportsbook":r.get("source",""),"game":r.get("game",""),
           "start":r["start"],"market_updated":r.get("market_updated") or odds["updated_at"],"over_odds":None,"under_odds":None,"features":features,
           "sample_games":len(history),"last_game":history[-1]["date"]})
        market["over_odds" if side=="More" else "under_odds"]=r.get("odds")
    paired=[v for v in raw_markets.values() if isinstance(v["over_odds"],int) and isinstance(v["under_odds"],int)]
    # The model projection remains independent. Evaluate it against the
    # median of independent real sportsbook prop lines instead of selecting
    # whichever book appears first. Preserve all source quotes for inspection.
    valid=consensus_markets(paired)
    print("Matched paired sportsbook quotes:",len(paired),
          "unique consensus markets:",len(valid),
          "markets with 2+ bookmakers:",sum(v["line_book_count"]>=2 for v in valid),flush=True)
    models={}
    for target in ("PTS","REB","AST","PRA"):
        models[target]=joblib.load(MODELS/f"{target}_model.joblib")
    defense_cache={}
    shadow_dir=ROOT/"models/nba/defense_shadow"
    shadow_models={}
    for stat in ("PTS","REB","AST","PRA"):
        file=shadow_dir/f"{stat}_model.joblib"
        if file.exists():
            shadow_models[stat]=joblib.load(file)
            if shadow_models[stat].get("status")!="SHADOW_ONLY_NOT_CALIBRATED":
                raise ValueError("Unrecognized opponent shadow model provenance")
    for row in valid:
        target=row["stat"];model=models[target]
        features=model["features"];fill=model["fill_values"]
        input_data={name:row["features"].get(name,fill.get(name,0)) for name in features}
        x=pd.DataFrame([input_data])[features].apply(pd.to_numeric,errors="coerce").fillna(0)
        projection=max(0,float(model["model"].predict(x)[0]))
        # Source-derived matchup context is descriptive only: the historical
        # models were NOT trained with opponent defensive features.
        pair=matchup(row["game"])
        upcoming_date=utc(row["start"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        if upcoming_date not in defense_cache:
            defense_cache[upcoming_date]=team_allowances(all_games,upcoming_date)
        opponent=pair[0] if pair[1]==row["team"] else pair[1]
        row["opponent"]=opponent
        row["opponent_defense"]=defense_context(defense_cache[upcoming_date],opponent,target)
        # Shadow forecast consumes opponent TEAM totals allowed before game date
        # with the same five defensively lagged inputs used in research training.
        # Do not infer a projection if the defensive record is missing.
        row["shadow_projection"]=None
        row["shadow_difference"]=None
        row["shadow_status"]="INSUFFICIENT_DEFENSE_DATA"
        opp_games=defense_cache[upcoming_date].get(opponent,[])
        if target in shadow_models and len(opp_games)>=3:
            sample=opp_games[-5:]
            def_values={f"OPP_{stat}_ALLOWED_L5":float(np.mean([v[stat] for _,v in sample]))
                        for stat in ("PTS","REB","AST","PRA")}
            def_values["OPP_DEF_SAMPLE_GAMES"]=min(5,len(opp_games))
            model_shadow=shadow_models[target]
            required=set(COLS)
            if required.issubset(model_shadow["features"]):
                all_features=dict(row["features"],**def_values)
                features_s=model_shadow["features"]
                x_shadow=pd.DataFrame([{name:all_features.get(name,model_shadow["fill_values"].get(name,0))
                                      for name in features_s}])[features_s].apply(pd.to_numeric,errors="coerce").fillna(0)
                shadow=max(0,float(model_shadow["model"].predict(x_shadow)[0]))
                row["shadow_projection"]=round(shadow,1)
                row["shadow_difference"]=round(shadow-row["line"],1)
                row["shadow_status"]="RESEARCH_SHADOW_ONLY"
        elif target not in shadow_models:
            row["shadow_status"]="SHADOW_MODEL_NOT_TRAINED"
        history=sorted(by_id.get(str(row["player_id"]),{}).values(),key=lambda x:x["date"])
        history=[g for g in history if g["date"]<upcoming_date]
        row["minutes_context"]=minutes_context(history)
        row["minutes_research"]=minutes_estimate(history,upcoming_date)
        row["minutes_v2_research"]=minutes_v2_forecast(
            history,upcoming_date,row["team"])
        row["shot_profile_research"]=shot_attempt_profile(
            history,upcoming_date,row["team"],
            row["minutes_v2_research"].get("expected_minutes"))
        recent_position=next((g.get("position") for g in reversed(history)
            if g.get("position")),None)
        row["position_group_context"]=positional_allowance(
            all_games,upcoming_date,opponent,recent_position,target)
        row["research_position"]=recent_position
        # Match official injury status by BOTH exact player ID and game date.
        # An NBA PDF can contain multiple dates and multiple team sections.
        official_report=report_fresh and injury_feed.get("status")=="OFFICIAL_NBA_REPORT_VERIFIED"
        generic_espn=report_fresh and injury_feed.get("status")=="THIRD_PARTY_ESPN_INJURY_CONTEXT"
        espn_same_day=generic_espn and issued.astimezone(
            ZoneInfo("America/New_York")).date().isoformat()==upcoming_date
        verified_status=(official_by_event.get((str(row["player_id"]),upcoming_date))
                         if official_report else
                         espn_by_id.get(str(row["player_id"])) if espn_same_day else None)
        if verified_status and verified_status.get("team")==row["team"] and verified_status.get("status")!="CONFLICTING_EXTRACT":
            row["injury_status"]=verified_status["status"].upper()
            row["injury_status_source"]=(
                "OFFICIAL_NBA_REPORT" if official_report
                else "ESPN_THIRD_PARTY_NOT_CONFIRMED")
            row["injury_report_url"]=injury_feed.get("source_pdf") or injury_feed.get("source_url")
        else:
            row["injury_status"]="NOT_VERIFIED"
            row["injury_status_source"]="UNAVAILABLE_OR_NOT_GAME_DAY"
        row["requires_lineup_review"]=True
        row["lineup_research_adjustment_applied"]=False
        row["teammate_absence_splits"]=[]
        if official_report:
            team_out=[p for (player_id,game_date),p in official_by_event.items()
                if game_date==upcoming_date and p.get("team")==row["team"]
                and str(p.get("status","")).upper()=="OUT"
                and player_id!=str(row["player_id"])]
            for teammate in team_out[:8]:
                observed=teammate_on_off(history,all_games,upcoming_date,teammate["player_id"],target)
                if observed:
                    row["teammate_absence_splits"].append({
                        "teammate":teammate["player"],**observed})
                if len(row["teammate_absence_splits"])>=2:break
        # Hypothetical injury-minute research requires an actual official NBA
        # game-date match. Third-party labels cannot trigger this scenario.
        row["injury_minutes_research"]=injury_minutes_research(
            history,all_games,upcoming_date,row["team"],
            team_out if official_report else [])
        row["defense_in_model"]=False
        row["projection"]=round(projection,1)
        # Build a combined median from UNROUNDED original and shadow forecasts.
        # Shadow model JSON stores a rounded research projection, so the
        # combination is approximately accurate to its displayed precision.
        combined=combine_projections(projection,
            row["shadow_projection"] if row["shadow_status"]=="RESEARCH_SHADOW_ONLY" else None)
        row["combined_projection"]=round(combined["projection"],1)
        row["combined_difference"]=round(combined["projection"]-row["line"],1)
        row["combined_method"]=combined["method"]
        row["combined_model_count"]=combined["model_count"]
        row["combined_validated"]=False
        row["projection_explanation"]=explain_projection(
            target,row["line"],projection,
            row["shadow_projection"] if row["shadow_status"]=="RESEARCH_SHADOW_ONLY" else None,
            combined["projection"],row["features"],row["minutes_context"],row["opponent_defense"],opponent=row["opponent"])
        row["combined_direction"]=("Over" if combined["projection"]>row["line"]
           else "Under" if combined["projection"]<row["line"] else "Neutral")
        row["difference"]=round(projection-row["line"],1)
        row["lean"]="Over" if row["difference"]>0 else "Under" if row["difference"]<0 else "Neutral"
        # This frequency is an experimental tail estimate from held-out
        # historical box-score errors; not market-validated odds or hit rates.
        row["estimated_over_probability"]=None
        row["estimated_under_probability"]=None
        row["estimated_push_probability"]=None
        row["estimated_selected_probability"]=None
        row["estimated_probability_side"]=None
        row["probability_method"]="UNAVAILABLE_NO_CHRONOLOGICAL_RESIDUALS"
        if "experimental_residuals" in model and model.get("residual_calibration",{}).get("real_market_calibrated") is False:
            frequency=probability_sides(projection,row["line"],model["experimental_residuals"])
            row["estimated_over_probability"]=round(frequency["over"],4)
            row["estimated_under_probability"]=round(frequency["under"],4)
            row["estimated_push_probability"]=round(frequency["push"],4)
            # Sort on the side suggested by the model's better estimated tail,
            # not the largest point gap. This side can differ from rounded
            # display projections near a market line.
            direction="Over" if frequency["over"]>frequency["under"] else "Under" if frequency["under"]>frequency["over"] else "Neutral"
            row["estimated_probability_side"]=direction
            row["estimated_selected_probability"]=round(max(frequency["over"],frequency["under"]),4)
            row["probability_method"]=METHOD
        row["ev_status"]="UNAVAILABLE_NO_VALIDATED_PROBABILITY"
        row["experimental_ev_available"]=False
        row["experimental_best_quote"]=None
        if "experimental_residuals" in model and model.get("residual_calibration",{}).get("real_market_calibrated") is False:
            quoted=[]
            for quote in row.get("book_quotes",[]):
                try:
                    priced=hypothetical_quote_analysis(quote,projection,model["experimental_residuals"])
                    quoted.append(priced)
                except (ValueError,TypeError,KeyError,OverflowError):
                    continue
            row["book_quotes"]=quoted
            if quoted:
                options=[]
                for quote in quoted:
                    for side in ("over","under"):
                        options.append({"book":quote["name"],"line":quote["line"],
                            "side":side.upper(),"odds":quote[side],
                            "hypothetical_ev_pct":quote["hypothetical_"+side+"_ev_pct"],
                            "model_probability":quote[side+"_model_probability"],
                            "market_no_vig":quote["market_no_vig_"+side]})
                row["experimental_best_quote"]=max(options,key=lambda item:item["hypothetical_ev_pct"])
                row["experimental_ev_available"]=True
                row["ev_status"]="HYPOTHETICAL_ONLY_UNCALIBRATED_PROBABILITIES"
        row["missing_features"]=[name for name in features if name not in row["features"]]
        del row["features"]
    valid.sort(key=lambda r:(
        r["estimated_selected_probability"] is not None,
        r["estimated_selected_probability"] if r["estimated_selected_probability"] is not None else -1,
        abs(r["difference"])),reverse=True)
    output={"generated_at":now.isoformat(),"last_form_update":form["updated_at"],
       "last_odds_update":odds["updated_at"],"status":"EXPERIMENTAL_NON_CALIBRATED",
       "verified_current_matchups":True,"is_prizepicks":False,
       "odds_input_file":ODDS.name,
       "games_with_ai_props":len({r["game"] for r in valid}),
       "injury_data_verified":report_fresh and injury_feed.get("status")=="OFFICIAL_NBA_REPORT_VERIFIED",
       "injury_context_source":injury_feed.get("status") if report_fresh else "UNAVAILABLE",
       "official_injury_report_url":injury_feed.get("source_pdf") if injury_feed.get("status")=="OFFICIAL_NBA_REPORT_VERIFIED" else None,
       "opponent_defense_applied_to_model":False,"lineup_research_adjustments_applied":False,
       "injury_minutes_research_status":"DESCRIPTIVE_ONLY_NOT_APPLIED",
       "minutes_baseline_validation":minutes_walkforward_backtest(all_games),
       "minutes_v2_validation":minutes_v2_backtest(all_games),
       "minutes_v2_applied_to_live_model":False,
       "shot_profile_applied_to_live_model":False,
       "opponent_shadow_available":bool(shadow_models),"shadow_is_primary":False,
       "line_aggregation_method":"MEDIAN_OF_DISTINCT_TWO_SIDED_BOOKMAKERS",
       "markets_with_multiple_books":sum(v["line_book_count"]>=2 for v in valid),
       "experimental_probability_ranking":True,
       "experimental_probability_method":METHOD,
       "real_market_probabilities_calibrated":False,
       "experimental_ev_available":True,
       "combined_projection_enabled":True,
       "combined_projection_validated":False,
       "combined_projection_method":"TWO_MODEL_MEDIAN_EQUAL_WEIGHT_RESEARCH_ONLY",
       "ev_verified":False,
       "ev_method":"PRICE_SPECIFIC_HYPOTHETICAL_EV_NOT_VALIDATED",
       "disclaimer":"Sportsbook reference lines use the median across distinct bookmakers where 2+ actual two-sided quotes exist, otherwise clearly labeled single-book fallback. Sportsbooks do NOT train or determine the player projection. Original historical-model predictions remain primary. Experimental model-side probabilities derive from past out-of-time box-score prediction errors, NOT verified sportsbook or PrizePicks win rates. Ranks can be inaccurate on real-market prop lines; player availability requires game-day verification, and research-only positional defense and minutes estimates do not change picks. Opponent-aware shadow is separate and research-only. The combined displayed projection is a two-model median (average) where a valid shadow forecast exists, falling back to original otherwise. Probabilities and EV still describe the ORIGINAL model only, not the combined projection; they are uncalibrated and cannot establish profitable picks.",
       "comparisons":valid,"skipped":skipped,
       "comparison_rows_published":len(valid),
       "comparison_rows_truncated":0}
    OUTPUT.write_text(json.dumps(output,indent=2)+"\n")
    print("Wrote",len(valid),"team-verified experimental model comparisons",flush=True)
    print("With descriptive opponent defense",sum(v["opponent_defense"] is not None for v in valid),flush=True)
    print("Rejected/unavailable",skipped,flush=True)

if __name__=="__main__":main()

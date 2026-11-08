"""Independently trained NBA projections vs genuine PrizePicks pick'em lines.

This research output is separate from priced sportsbook research. It never
substitutes pick'em tiers for American odds or calls any betting API.
"""
import json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import joblib
import numpy as np
import pandas as pd

try:
    from .compare_live_models import key,matchup,predict_features,utc
    from .combined_projection import combine_projections
    from .matchup_context import team_allowances
    from .defense_training import COLS
except ImportError:
    from compare_live_models import key,matchup,predict_features,utc
    from combined_projection import combine_projections
    from matchup_context import team_allowances
    from defense_training import COLS

try:
    from .minutes_v3_research import forecast as minutes_v3_forecast, team_context
    from .opportunity_v2_research import forecast as opportunity_v2_forecast
    from .tracking_opportunity_features import load_tracking
except ImportError:
    from minutes_v3_research import forecast as minutes_v3_forecast, team_context
    from opportunity_v2_research import forecast as opportunity_v2_forecast
    from tracking_opportunity_features import load_tracking

ROOT=Path(__file__).resolve().parents[1]
ET=ZoneInfo("America/New_York")
STATS=("PTS","REB","AST","PRA")

def generate(feed,form,current_games,models,shadows=None,now=None,injuries=None):
    now=now or datetime.now(timezone.utc)
    shadows=shadows or {}
    injuries=injuries or {}
    report_valid=(injuries.get("status")=="OFFICIAL_NBA_REPORT_VERIFIED"
                  and injuries.get("injury_data_verified") is True)
    try:
        issued=utc(injuries["report_issued_at"])
        report_valid=report_valid and 0<=(now-issued).total_seconds()<=18*3600
    except (KeyError,ValueError,TypeError):
        report_valid=False
    unavailable={}
    if report_valid:
        for p in injuries.get("players",[]):
            if not isinstance(p,dict):continue
            if str(p.get("status","")).upper() not in ("OUT","DOUBTFUL"):continue
            if p.get("game_date") and p.get("player_id") and p.get("team"):
                unavailable[(str(p["player_id"]),str(p["team"]),str(p["game_date"]))]=str(p["status"]).upper()
    if feed.get("status")!="LIVE_THIRD_PARTY_PRIZEPICKS_LINES":
        raise ValueError("Only real, independently authenticated provider feed allowed")
    if form.get("season")!="2026-27" or (now-utc(form["updated_at"])).total_seconds()>48*3600:
        raise ValueError("Missing or stale NBA 2026-27 player form")
    if (now-utc(feed["generated_at"])).total_seconds()>6*3600:
        raise ValueError("PrizePicks source no longer a current observation")
    roster=defaultdict(list)
    for r in form["players"]:roster[key(r["player"])].append(r)
    history=defaultdict(dict)
    for r in current_games:history[str(r["id"])][r["date"]]=r
    team_presence=team_context(current_games)
    tracking_rows,tracking_coverage=load_tracking()
    eligible=[]
    skipped=Counter()
    cache={}
    for offer in feed.get("board_offers",[]):
        try:
            start=utc(offer["starts_at"])
            observed=utc(offer["observed_at"])
            stat=offer["stat"]
            if start<=now or stat not in STATS or observed>now or now-observed>__import__("datetime").timedelta(hours=6):
                skipped["not_upcoming_or_observation_stale"]+=1
                continue
            if offer.get("source")!="independent_prizepicksapi_com" or offer.get("is_demo") is not False:
                skipped["not_verified_live_provider"]+=1
                continue
            pair=matchup(offer["game"])
            people=roster[key(offer["player"])]
            if not pair or len(people)!=1 or people[0]["team"]!=offer["team"] or offer["team"] not in pair:
                skipped["missing_or_ambiguous_roster_team"]+=1
                continue
            person=people[0]
            date=start.astimezone(ET).date()
            if unavailable.get((str(person["player_id"]),str(offer["team"]),date.isoformat())):
                skipped["official_game_day_out_or_doubtful"]+=1
                continue
            dates=sorted(history[str(person["player_id"])].values(),key=lambda g:g["date"])
            past=[x for x in dates if datetime.fromisoformat(x["date"]).date()<date]
            if len(past)<5:
                skipped["insufficient_completed_current_season_games"]+=1;continue
            token=(str(person["player_id"]),start.isoformat(),stat)
            if token not in cache:
                base=predict_features(past,date,offer["team"]==pair[1])
                if base is None:
                    skipped["feature_input_missing"]+=1;continue
                model=models.get(stat)
                if not model:skipped["model_unavailable"]+=1;continue
                cols=model["features"]
                x=pd.DataFrame([{c:base.get(c,model["fill_values"].get(c,0)) for c in cols}])[cols]
                original=max(0,float(model["model"].predict(x)[0]))
                opponent=pair[0] if offer["team"]==pair[1] else pair[1]
                shadow=None
                # Defensive model requires strictly prior opponent games.
                if stat in shadows:
                    allowed=team_allowances(current_games,date.isoformat()).get(opponent,[])
                    if len(allowed)>=3:
                        sample=allowed[-5:]
                        shadow_model=shadows[stat]
                        if shadow_model.get("status")=="SHADOW_ONLY_NOT_CALIBRATED" and set(COLS).issubset(shadow_model["features"]):
                            def_values={f"OPP_{name}_ALLOWED_L5":float(np.mean([v[name] for _,v in sample]))
                                        for name in ("PTS","REB","AST","PRA")}
                            def_values["OPP_DEF_SAMPLE_GAMES"]=min(5,len(allowed))
                            features={**base,**def_values}
                            shadow_cols=shadow_model["features"]
                            sx=pd.DataFrame([{c:features.get(c,shadow_model["fill_values"].get(c,0)) for c in shadow_cols}])[shadow_cols]
                            shadow=max(0,float(shadow_model["model"].predict(sx)[0]))
                combo=combine_projections(original,shadow)
                cache[token]=(original,shadow,combo,base,len(past))
            original,shadow,combined,base,n_games=cache[token]
            line=float(offer["line"])
            projection=round(combined["projection"],1)
            direction=("MORE" if projection>line else "LESS" if projection<line else "NO_LEAN")
            official_out_teammates=[
                pid for (pid,t,d),status in unavailable.items()
                if report_valid and t==offer["team"] and d==date.isoformat()
                and status=="OUT" and pid!=str(person["player_id"])]
            minutes_v3=minutes_v3_forecast(past,date.isoformat(),offer["team"],
                player_id=person["player_id"],team_games=team_presence,
                verified_out_ids=official_out_teammates,
                pretip_injury_verified=report_valid)
            opportunity_v2=opportunity_v2_forecast(
                past,date.isoformat(),offer["team"],
                player_id=person["player_id"],minutes=minutes_v3,
                baseline_by_stat={stat:combined["projection"]} if stat in ("AST","REB") else {},
                tracking=tracking_rows)
            eligible.append({
                "provider_projection_id":str(offer["id"]),
                "player":offer["player"],"player_id":str(person["player_id"]),
                "team":offer["team"],"game":offer["game"],"start":start.isoformat(),
                "stat":stat,"line":line,"more_tier":offer.get("more_tier"),
                "less_tier":offer.get("less_tier"),
                "observed_at":observed.isoformat(),
                "original_projection":round(original,1),
                "opponent_aware_projection":round(shadow,1) if shadow is not None else None,
                "combined_projection":projection,"combined_method":combined["method"],
                "ai_direction":direction,"model_count":combined["model_count"],
                "season_observations":n_games,
                "pts_l5":round(base.get("PTS_L5",0),2),
                "minutes_l5":round(base.get("MIN_L5",0),2),
                "minutes_v3_research":minutes_v3,
                "opportunity_v2_research":opportunity_v2
                    if stat in ("AST","REB") else None,
                "minutes_v2_research_baseline":base.get("MIN_L5"),
                "captured_at":now.isoformat(),
                "no_calibrated_hit_percentage":True,"no_verified_ev":True,
                "source":"independent_prizepicksapi_com"})
        except (KeyError,ValueError,TypeError,OverflowError):
            skipped["invalid_source_or_model_inputs"]+=1
    return {"status":"PRIZEPICKS_AI_RESEARCH_ONLY_NOT_SPORTSBOOK_ODDS",
        "generated_at":now.isoformat(),"provider_generated_at":feed["generated_at"],
        "minutes_v3_opportunity_v2_research_only":True,
        "tracking_coverage":tracking_coverage,
        "comparison_count":len(eligible),
        "games_with_ai_comparisons":len({x["game"] for x in eligible}),
        "by_game":dict(Counter(x["game"] for x in eligible)),
        "source_eligible_markets":len(feed.get("board_offers",[])),
        "skipped":dict(skipped),"comparisons":eligible,
        "confidence_calibrated":False,"sportsbook_american_odds_available":False,
        "paper_pick_ledger_modified":False,"existing_combined_ai_modified":False}

def main():
    feed=json.loads((ROOT/"docs/prizepicks_site.json").read_text())
    form=json.loads((ROOT/"docs/current_form.json").read_text())
    games=json.loads((ROOT/"data/nba/current/current_games.json").read_text())
    models={}
    shadows={}
    for stat in STATS:
        models[stat]=joblib.load(ROOT/f"models/nba/provisional/{stat}_model.joblib")
        source=ROOT/f"models/nba/defense_shadow/{stat}_model.joblib"
        if source.exists():shadows[stat]=joblib.load(source)
    injury_path=ROOT/"docs/injury_context.json"
    injuries=json.loads(injury_path.read_text()) if injury_path.exists() else {}
    try:
        data=generate(feed,form,games,models,shadows,injuries=injuries)
    except ValueError as error:
        # Provider exhaustion/stale snapshots are not model failures.
        # Never republish the old prop board with a fresh timestamp.
        known_unavailable={
            "PrizePicks source no longer a current observation",
            "Only real, independently authenticated provider feed allowed",
            "Missing or stale NBA 2026-27 player form"}
        if str(error) in known_unavailable:
            print("No verified fresh PrizePicks provider observation; "
                  "preserving existing pretip research and skipping predictions")
            return
        raise
    if not data["comparisons"]:
        print("No supported upcoming PrizePicks player/model comparisons; not replacing previous nonempty archive")
        return
    (ROOT/"docs/prizepicks_ai_research.json").write_text(json.dumps(data,separators=(",",":"))+"\n")
    print("PRIZEPICKS AI RESEARCH:",data["comparison_count"],
          "props",data["games_with_ai_comparisons"],"games",
          "sources",data["source_eligible_markets"],"skipped",data["skipped"],flush=True)
if __name__=="__main__":main()

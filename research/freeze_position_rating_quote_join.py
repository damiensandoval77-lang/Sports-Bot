"""Link actual quoted standard NBA props to only PREEXISTING matchup source snapshots.

A source published after the quote freeze is not attached retroactively.
No grades or existing predictions are mutated. Descriptive matchup projection
is research only; percent HIT EST remains blocked pending calibration.
"""
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from research.position_rating_hit_candidate import POSITIONS,MARKETS,finite,time

def select_picks(snapshot):
    picks=snapshot.get("predictions",[])
    if snapshot.get("status")!="LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED" or not isinstance(picks,list):
        raise ValueError("expected original frozen snapshot, not invented props")
    return picks

def key(x):
    return (str(x.get("player_id")),str(x.get("team")),str(x.get("opponent")))

def assemble(snapshot,joined,ratings,*,captured_at):
    now=time(captured_at)
    if joined.get("status")!="SOURCED_MATCHUP_CONTEXT_RESEARCH_NOT_LIVE":
        raise ValueError("unverified research context")
    if ratings.get("status")!="SOURCED_ESTIMATED_DEF_RATING_RESEARCH" or ratings.get("team_count")!=30:
        raise ValueError("unverified defensive rating source")
    if time(joined["captured_at"])>now or time(ratings["captured_at"])>now:
        raise ValueError("future research source")
    context={}
    for p in joined.get("player_records",[]):
        k=key(p)
        if k in context:raise ValueError("duplicate player/team/opponent")
        context[k]=p
    results=[]
    reasons=Counter()
    for p in select_picks(snapshot):
        if p.get("pickem_tier")!="standard" or p.get("standard_line_two_sided_verified") is not True:
            reasons["nonstandard_or_unverified_line"]+=1;continue
        if str(p.get("stat")) not in MARKETS or not p.get("player_id"):
            reasons["unsupported_market_or_identity"]+=1;continue
        try:
            freeze=time(p["captured_at"])
            tip=time(p["start"])
            if not freeze<tip:
                reasons["not_frozen_pregame"]+=1;continue
            if tip<=now:
                reasons["game_already_started"]+=1;continue
            line=finite(p["line"],"original standard line")
            base=finite(p["projection"],"original projection",positive=True)
            if line<0:raise ValueError("invalid line")
        except (ValueError,KeyError,TypeError):
            reasons["invalid_original_market"]+=1;continue
        c=context.get(key(p))
        if not c:
            reasons["no_exact_player_opponent_context"]+=1;continue
        if time(c["start"])!=tip:
            reasons["matchup_game_time_mismatch"]+=1;continue
        # As-of means the source was ACTUALLY published before quote capture;
        # do not retrofit the quote with later research run information.
        if (time(joined["captured_at"])>freeze or time(c["captured_at"])>freeze or
            time(ratings["captured_at"])>freeze):
            reasons["source_not_available_when_pick_frozen"]+=1;continue
        pos=c.get("listed_position")
        if pos not in POSITIONS:
            reasons["unknown_listed_position"]+=1;continue
        stats=c.get("opponent_position_allowance_ratio_by_stat_research")
        if not isinstance(stats,dict) or p["stat"] not in stats:
            reasons["insufficient_opponent_position_samples"]+=1;continue
        raw_ratio=finite(stats[p["stat"]],"position allowance ratio",positive=True)
        if not c.get("opponent_defense_sample_games",0)>=5:
            reasons["insufficient_opponent_defense_games"]+=1;continue
        rating=ratings["teams"].get(p["opponent"])
        if not isinstance(rating,dict) or rating["team"]!=p["opponent"]:
            reasons["opponent_rating_unavailable"]+=1;continue
        if rating.get("metric")!="ESTIMATED_POINTS_ALLOWED_PER_100_POSSESSIONS":
            reasons["rating_metric_is_not_def_rating"]+=1;continue
        if time(rating.get("observed_at"))>freeze:
            reasons["opponent_def_rating_postcapture"]+=1;continue
        def_rating=finite(rating["defensive_rating"],"team def rating",positive=True)
        league_rating=finite(rating["league_defensive_rating"],"league def rating",positive=True)
        proj_minutes=c.get("research_minutes_forecast")
        observed=c.get("observed_minutes_last3")
        if proj_minutes is None or observed is None:
            reasons["minutes_unavailable"]+=1;continue
        proj_minutes=finite(proj_minutes,"projected minutes",positive=True)
        observed=finite(observed,"historical minutes reference",positive=True)
        if c.get("player_injury_status") in ("Out","Doubtful"):
            reasons["official_injury_unavailable"]+=1;continue
        # Research-only damped sensitivity; NOT a fitted, calibrated chance.
        role_effect=max(.9,min(1.1,raw_ratio**.25))
        team_effect=max(.96,min(1.04,(def_rating/league_rating)**.1))
        minutes_effect=max(.6,min(1.4,proj_minutes/observed))
        adjusted=round(base*role_effect*team_effect*minutes_effect,3)
        results.append({
            "player_id":str(p["player_id"]),"player":p.get("player"),
            "team":p["team"],"opponent":p["opponent"],"stat":p["stat"],
            "position":pos,"start":p["start"],"pick_captured_at":p["captured_at"],
            "original_line":line,"original_projection":base,
            "experimental_matchup_projection":adjusted,
            "model":"POSITION_V_POSITION_DEF_RATING_RESEARCH_V1",
            "source_provenance":{
                "position_observed_at":c["asof_source_times"]["position_source"],
                "player_observed_at":c["asof_source_times"]["player_form"],
                "rating_observed_at":rating["observed_at"],
                "rating_source":rating["source"],
                "minutes_snapshot_at":c["asof_source_times"]["minutes_snapshot"]},
            "direction":(p.get("estimated_hit_chance") or {}).get("modeled_direction"),
            "hit_probability":None,"calibrated":False,
            "production_approved":False,"source_frozen_before_quote":True})
    return {
        "status":"RESEARCH_QUOTE_MATCHUP_JOIN_NO_PRODUCTION_HIT_EST",
        "captured_at":captured_at,"input_quotes":len(select_picks(snapshot)),
        "qualified_experimental_projections":len(results),
        "results":results,"exclusions":dict(sorted(reasons.items())),
        "production_approved":False,"probabilities_generated":0,
        "note":"Only source-time-safe original standard lines may be associated. Do not retroactively alter line, projection or grade; no live percentages until calibrated."
    }
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--quotes",default="docs/lagged_matchup_live_all_markets.json")
    ap.add_argument("--joined",default="joined-matchup-features-research.json")
    ap.add_argument("--ratings",default="defensive-rating-research.json")
    ap.add_argument("--output",default="position-rating-quote-research.json")
    args=ap.parse_args()
    result=assemble(json.loads(Path(args.quotes).read_text()),
        json.loads(Path(args.joined).read_text()),
        json.loads(Path(args.ratings).read_text()),
        captured_at=datetime.now(timezone.utc).isoformat())
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:result[k] for k in ("status","input_quotes",
       "qualified_experimental_projections","exclusions","probabilities_generated")},indent=2))
if __name__=="__main__":main()

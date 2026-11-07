"""Pregame-only predicted defensive assignment research.

The target is a probability-like *allocation of candidate defender possessions*
(not a calibrated probability or an actual confirmed assignment).

Uses exclusively earlier player-vs-defender possession history, previous team
rotation minutes, switches and optionally archived position labels. When
unobserved matchups dominate, leaves significant neutral/unassigned exposure.
Does not ingest same-day game data or touch live AI.
"""
import math
from collections import defaultdict
from datetime import date

# Fixed ex-ante research coefficients, never tuned on held-out games.
MIN_ROTATION_PLAYERS=3
LOOKBACK_DAYS=45
PAST_MATCHUP_PRIOR=35.0
ROLE_PRIOR=0.70
NEUTRAL_EXPOSURE=0.25
SWITCH_PENALTY=0.40
MAX_ADJUSTMENT=2.0


def positional_group(value):
    """Only recognize actual provided source positions; do not invent roles."""
    val=str(value or "").strip().upper()
    if val in ("G","PG","SG","G-F"):return "G"
    if val in ("F","SF","PF","F-G","F-C"):return "F"
    if val in ("C","C-F"):return "C"
    return None


def position_affinity(off_position,def_position):
    offense=positional_group(off_position)
    defender=positional_group(def_position)
    if not offense or not defender:return 1.
    return 1.12 if offense==defender else ROLE_PRIOR


def projected_assignment(off_id,opponent_team,rotation,pair_history,positions,as_of):
    """Calculate defender shares using only pre-existing, validated history.

    rotation: (defender_id, expected_minutes) for opponent-team players only,
      sourced from earlier 5 player games.
    pair_history: (off_id,def_id) -> {poss,switches,last_seen,off_team,def_team,...}
      recorded from games STRICTLY preceding as_of.
    The forecast must not imply these defenders are confirmed starters.
    """
    out={"status":"UNVERIFIED_DEFENDER_ASSIGNMENT",
         "candidate_defenders":[],"unassigned_share":1.0,
         "predicted_top_defender":None,
         "top_defender_share":None,
         "confirmed_assignment":False,
         "source":"PAST_MATCHUP_POSSESSIONS_SWITCHES_AND_ROTATION_MINUTES"}
    try:target=date.fromisoformat(str(as_of)[:10])
    except ValueError:return {**out,"status":"INVALID_TARGET_DATE"}
    if len(rotation)<MIN_ROTATION_PLAYERS:
        return {**out,"status":"INSUFFICIENT_OPPONENT_ROTATION"}
    pairs=[]
    for defender_id,minutes in rotation:
        key=(str(off_id),str(defender_id))
        prior=pair_history.get(key)
        if minutes<=0 or prior is None:continue
        if prior.get("def_team")!=opponent_team:continue
        try:
            recent_day=date.fromisoformat(str(prior.get("last_seen"))[:10])
            age=(target-recent_day).days
        except ValueError:continue
        if age<=0 or age>LOOKBACK_DAYS:continue
        possessions=float(prior.get("poss",0))
        switches=float(prior.get("switches",0))
        if not math.isfinite(possessions) or not math.isfinite(switches) or possessions<5 or switches<0:continue
        # Don't infer which player is a confirmed primary defender.
        role=position_affinity(positions.get(str(off_id)),positions.get(str(defender_id)))
        continuity=max(0.0,1.0-age/75)
        switch_discount=1-SWITCH_PENALTY*min(1.0,switches/max(possessions,1.))
        confidence=possessions/(possessions+PAST_MATCHUP_PRIOR)
        score=minutes*role*continuity*switch_discount*confidence
        if score>0:pairs.append((str(defender_id),score,possessions,minutes))
    if not pairs:return {**out,"status":"NO_RECENT_DIRECT_ASSIGNMENT_EVIDENCE"}
    # Neutral share intentionally prevents overclaiming that all matchup
    # possessions can be forecast from historical head-to-head data.
    total=sum(x[1] for x in pairs)
    denominator=total/(1-NEUTRAL_EXPOSURE)
    ranked=sorted(pairs,key=lambda x:(-x[1],x[0]))
    candidates=[{"def_player_id":p,"estimated_exposure_share":round(score/denominator,5),
        "past_matchup_possessions":round(poss,1),"projected_minutes_proxy":round(minutes,1)}
        for p,score,poss,minutes in ranked]
    return {**out,"status":"HISTORICAL_ASSIGNMENT_PROJECTION_RESEARCH_ONLY",
        "candidate_defenders":candidates,
        "predicted_top_defender":ranked[0][0],
        "top_defender_share":candidates[0]["estimated_exposure_share"],
        "unassigned_share":round(NEUTRAL_EXPOSURE,5)}


def assignment_points_scenario(baseline,assignment,pair_history,off_id):
    """Apply shot-specific historical pair residuals to exposure fractions."""
    if assignment["status"]!="HISTORICAL_ASSIGNMENT_PROJECTION_RESEARCH_ONLY":
        return None
    p2=baseline["expected_2p_pct"]
    p3=baseline["expected_3p_pct"]
    delta=0.
    for candidate in assignment["candidate_defenders"]:
        prior=pair_history.get((str(off_id),candidate["def_player_id"]))
        if not prior:continue
        a2=prior.get("two_a",0.)
        a3=prior.get("three_a",0.)
        if a2+a3<3:continue
        diff2=(prior["two_m"]+80*p2)/(a2+80)-p2
        diff3=(prior["three_m"]+60*p3)/(a3+60)-p3
        share=candidate["estimated_exposure_share"]
        delta+=share*(2*baseline["expected_2pa"]*diff2+
                      3*baseline["expected_3pa"]*diff3)
    adjusted=max(-MAX_ADJUSTMENT,min(MAX_ADJUSTMENT,0.65*delta))
    return round(max(0,baseline["expected_points"]+adjusted),3)


def evaluate_assignment(actual_by_player,precomputed_forecasts):
    """Paired diagnostics; no model tuning or inferred win rate."""
    n=0
    correct=0
    baseline_correct=0
    for key,forecast in precomputed_forecasts.items():
        target=actual_by_player.get(key)
        if not target or forecast["status"]!="HISTORICAL_ASSIGNMENT_PROJECTION_RESEARCH_ONLY":continue
        # Actual dominant defender is observable *after* the game only.
        if not target.get("top_defender"):continue
        n+=1
        correct+=int(forecast["predicted_top_defender"]==target["top_defender"])
        baseline_correct+=int(forecast.get("minutes_only_top")==target["top_defender"])
    return {"eligible_games":n,
            "predicted_top_defender_accuracy":round(correct/n,4) if n else None,
            "minutes_only_top_defender_accuracy":round(baseline_correct/n,4) if n else None,
            "predictive_assignments_unverified":True}

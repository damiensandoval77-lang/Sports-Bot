"""Deterministic 20,000-draw research forecast using chronological residuals.

Residuals are from the ORIGINAL model. Centering them on a COMBINED forecast
is an explicit modeling assumption, NOT verified combined-model calibration.
No market-implied probability, EV or betting edge is claimed.
"""
import hashlib
import numpy as np

METHOD = "COMBINED_PROJECTION_20K_ORIGINAL_RESIDUAL_BOOTSTRAP_UNCALIBRATED"
DRAWS = 20000

def simulate_combined_hit_rate(combined_projection, line, residuals, identity, draws=DRAWS,
                               opponent=None, defense_history=None, opponent_defense=None):
    center = float(combined_projection)
    threshold = float(line)
    errors = np.asarray(residuals, dtype=float)
    errors = errors[np.isfinite(errors)]
    if not (np.isfinite(center) and np.isfinite(threshold)) or len(errors) < 1000:
        raise ValueError("Chronological residual validation sample unavailable")
    if draws != DRAWS:
        raise ValueError("Research simulation count must be 20,000")
    seed = int.from_bytes(hashlib.sha256(str(identity).encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    sampled_errors = rng.choice(errors, size=draws, replace=True)
    # A matchup-aware forecast center already includes the opponent shadow.
    # Never multiply the entire center by the opponent vs-league percentage:
    # that would count opponent defense TWICE. Instead model game-to-game
    # variation in this specific defense's historical allowed totals.
    conditioning={"status":"UNAVAILABLE_INSUFFICIENT_PRIOR_DEFENSE",
                  "opponent":opponent,"scope":"TEAM_TOTALS_NOT_POSITIONAL",
                  "mean_shift_applied":False,"adjustment_strength":0.0,
                  "opponent_vs_league_pct":None}
    scenario_noise=np.zeros(draws,dtype=float)
    if isinstance(opponent_defense,dict) and opponent_defense.get("opponent")==opponent:
        try:
            allowed=np.asarray(defense_history,dtype=float).reshape(-1)
            allowed=allowed[np.isfinite(allowed)&(allowed>=0)]
            league=float(opponent_defense["league_avg"])
            report_pct=float(opponent_defense["vs_league_pct"])
        except (TypeError,ValueError,KeyError):
            allowed=np.array([]);league=np.nan;report_pct=np.nan
        if len(allowed)>=5 and np.isfinite(league) and league>0 and np.isfinite(report_pct):
            allowed=allowed[-10:]
            avg=float(np.mean(allowed))
            # The opponent allowed % is explicitly used as the normalization
            # anchor for each defensive game scenario. Subtract its own mean,
            # so no additional average defensive effect is applied.
            actual_vs_league=avg/league
            if avg>0 and 0.25<=actual_vs_league<=4.0:
                ratios=(allowed/league)/actual_vs_league
                # Bounded research-only variation: 25% weight on a
                # historical opponent game, max 10% swing in player center.
                # It is NOT a calibrated model of defender/player variance.
                bounded=np.clip(0.25*(ratios-1),-0.10,0.10)
                bounded=bounded-np.mean(bounded)
                sampled=rng.choice(bounded,size=draws,replace=True)
                scenario_noise=center*sampled
                conditioning={
                    "status":"APPLIED_OPPONENT_HISTORICAL_GAME_SCENARIOS",
                    "opponent":opponent,"scope":"TEAM_TOTALS_NOT_POSITIONAL",
                    "source_games":len(allowed),
                    "opponent_vs_league_pct":round(report_pct,2),
                    "recent_allowed_avg":round(avg,2),
                    "league_allowed_avg":round(league,2),
                    "adjustment_strength":0.25,
                    "max_game_scenario_shift":0.10,
                    "mean_shift_applied":False,
                    "center_opponent_aware_already":True,
                    "position_dvp_available":False,
                }
    simulated = np.maximum(0.0, center + sampled_errors + scenario_noise)
    over = int(np.count_nonzero(simulated > threshold))
    under = int(np.count_nonzero(simulated < threshold))
    push = draws - over - under
    direction = "Over" if center > threshold else "Under" if center < threshold else "Neutral"
    hit = over if direction == "Over" else under if direction == "Under" else None
    return {
        "method": METHOD, "simulation_count": draws,
        "over_hit_rate": round(over / draws, 4),
        "under_hit_rate": round(under / draws, 4),
        "push_rate": round(push / draws, 4),
        "direction": direction,
        "selected_hit_rate": round(hit / draws, 4) if hit is not None else None,
        "calibrated": False,
        "residual_provenance": "ORIGINAL_MODEL_CHRONOLOGICAL_HOLDOUT",
        "combined_residuals_validated": False,
        "independent_game_outcomes": False,
        "opponent_conditioning": conditioning
    }

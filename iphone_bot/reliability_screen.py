"""Pregame-only reliability screen. Does not claim improved hit rate.

Blocks recommendation-level confidence when known structural risks are present.
Always retain projections for research and future unbiased settlement.
"""
import math

def research_screen(row):
    reasons = []
    line = float(row["line"])
    combined = float(row["combined_projection"])
    original = float(row["projection"])
    shadow = row.get("shadow_projection")
    if not all(math.isfinite(x) for x in (line, combined, original)):
        return {"status":"ABSTAIN", "reasons":["INVALID_FORECAST"], "validated":False}
    if abs(combined - line) < 0.05:
        reasons.append("NO_DIRECTIONAL_EDGE")
    if int(row.get("sample_games") or 0) < 10:
        reasons.append("SHORT_PLAYER_HISTORY")
    if shadow is None or row.get("shadow_status") != "RESEARCH_SHADOW_ONLY":
        reasons.append("OPPONENT_MODEL_UNAVAILABLE")
    else:
        opponent = float(shadow)
        if not math.isfinite(opponent) or (original-line)*(opponent-line) <= 0:
            reasons.append("ORIGINAL_OPPONENT_DISAGREE")
    if row.get("injury_reprojection_status") == "INSUFFICIENT_VERIFIED_PRIOR_ON_OFF_EVIDENCE":
        reasons.append("UNRESOLVED_MATERIAL_INJURY")
    if row.get("injury_reprojection_status") == "REPROJECTED_FROM_VERIFIED_OFFICIAL_OUT":
        reasons.append("UNVALIDATED_INJURY_ADJUSTMENT")
    if row.get("injury_status_source") != "OFFICIAL_NBA_REPORT":
        reasons.append("PLAYER_AVAILABILITY_NOT_OFFICIALLY_VERIFIED")
    sim = row.get("combined_simulation") or {}
    if sim.get("simulation_count") != 20000 or sim.get("selected_hit_rate") is None:
        reasons.append("COMBINED_SIMULATION_UNAVAILABLE")
    # No selection is called proven even when no flags are present.
    return {
        "status":"ABSTAIN" if reasons else "RESEARCH_ONLY",
        "reasons":reasons,
        "validated":False,
        "wager_recommended":False,
        "screen_method":"PREGAME_STRUCTURE_AND_SOURCE_FLAGS_V1"
    }

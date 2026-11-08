"""Pregame structural research screen: actionable MODEL LEAN vs genuine PASS.

A displayed MODEL_LEAN is a directional research pick, not a proven advantage,
calibrated probability, verified payout EV, or guaranteed profitable bet.
Warnings stay visible, but do not falsely veto every early-season prop.
"""
import math

MIN_GAMES = 5
MARGINS = {"PTS": 1.5, "REB": 0.75, "AST": 0.75, "PRA": 2.0}
HARD_INJURY = {"OUT", "DOUBTFUL"}

def research_screen(row):
    blockers = []
    cautions = []
    try:
        line = float(row["line"])
        combined = float(row["combined_projection"])
        original = float(row["projection"])
    except (TypeError, ValueError, KeyError):
        return _result("PASS", None, ["INVALID_FORECAST"], [])
    if not all(math.isfinite(x) for x in (line, combined, original)):
        return _result("PASS", None, ["INVALID_FORECAST"], [])

    market = row.get("stat")
    margin = MARGINS.get(market)
    gap = combined - line
    side = "MORE" if gap > 0 else "LESS" if gap < 0 else None
    if margin is None:
        blockers.append("UNSUPPORTED_MARKET")
    elif abs(gap) < margin:
        blockers.append("SMALL_PROJECTION_EDGE")

    history = int(row.get("sample_games") or 0)
    if history < MIN_GAMES:
        blockers.append("INSUFFICIENT_RECENT_PLAYER_GAMES")
    elif history < 10:
        cautions.append("EARLY_SEASON_SHORT_HISTORY")

    shadow = row.get("shadow_projection")
    if shadow is None or row.get("shadow_status") != "RESEARCH_SHADOW_ONLY":
        cautions.append("OPPONENT_MODEL_UNAVAILABLE")
    else:
        try:
            opponent = float(shadow)
            if not math.isfinite(opponent):
                blockers.append("INVALID_OPPONENT_FORECAST")
            elif (original - line) * (opponent - line) <= 0:
                blockers.append("MODELS_DISAGREE_OR_TIE")
        except (TypeError, ValueError):
            blockers.append("INVALID_OPPONENT_FORECAST")

    injury = row.get("injury_reprojection_status")
    if injury == "INSUFFICIENT_VERIFIED_PRIOR_ON_OFF_EVIDENCE":
        blockers.append("UNRESOLVED_MATERIAL_INJURY")
    elif injury == "REPROJECTED_FROM_VERIFIED_OFFICIAL_OUT":
        cautions.append("UNVALIDATED_INJURY_ADJUSTMENT")
    player_status = str(row.get("injury_status") or "").upper()
    if player_status in HARD_INJURY:
        blockers.append("PLAYER_LISTED_"+player_status)
    elif player_status in ("QUESTIONABLE", "GTD"):
        blockers.append("PLAYER_AVAILABILITY_UNCERTAIN")
    # A healthy player may simply be absent from the NBA injury report.
    if row.get("injury_status_source") != "OFFICIAL_NBA_REPORT":
        cautions.append("OFFICIAL_PLAYER_STATUS_NOT_CONFIRMED")

    sim = row.get("combined_simulation") or {}
    valid_sim = (sim.get("simulation_count") == 20000 and
                 sim.get("selected_hit_rate") is not None and
                 sim.get("direction") == ("Over" if side == "MORE" else "Under" if side == "LESS" else None) and
                 sim.get("calibrated") is False)
    if not valid_sim:
        cautions.append("UNVALIDATED_OR_UNAVAILABLE_COMBINED_SIMULATION")
    else:
        cautions.append("SIMULATION_NOT_MARKET_CALIBRATED")

    return _result("PASS" if blockers else "MODEL_LEAN", side if not blockers else None,
                   blockers, cautions, gap=round(gap, 3), min_gap=margin)

def _result(status, side, blockers, cautions, gap=None, min_gap=None):
    return {
        "status": status,
        "side": side,
        "blockers": blockers,
        "cautions": cautions,
        # backward-compatible reasons for earlier clients
        "reasons": blockers + cautions,
        "edge_units": gap,
        "required_edge_units": min_gap,
        "validated": False,
        "wager_recommended": False,
        "screen_method": "PREGAME_MODEL_LEAN_REVIEW_V2_UNVALIDATED"
    }

"""Research-only, point-in-time features from authorized statistical snapshots.

Fail closed when identity or freshness is ambiguous. Snapshot aggregates are
NOT individual game outcomes, positional allowances, or defender matchups.
No production forecast/pick is changed by this module.
"""
from datetime import date, datetime

try:
    from .external_stats_snapshot import SnapshotError
except ImportError:
    from external_stats_snapshot import SnapshotError


def _day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as exc:
        raise SnapshotError("Invalid event date") from exc


def build_pregame_features(player_snapshot, team_snapshot, player_id_map, *,
                           player_id, team, opponent, event_date):
    """Build features only from strictly earlier dated, licensed snapshots.

    player_id_map must be a curated dictionary keyed by (player name, team)
    and valued by a stable basketball player ID. Unknown or ambiguous IDs are
    rejected; names alone never identify players in prediction pipelines.
    """
    if not isinstance(player_id_map, dict) or not player_id_map:
        raise SnapshotError("Verified player ID map required")
    game_day = _day(event_date)
    for snap, kind in ((player_snapshot, "player"), (team_snapshot, "team")):
        if snap.get("kind") != kind or snap.get("status") != "VALIDATED_OFFLINE_RESEARCH_ONLY":
            raise SnapshotError("Unvalidated snapshot")
        if snap.get("season") != player_snapshot.get("season"):
            raise SnapshotError("Season mismatch")
        if _day(snap.get("as_of")) >= game_day:
            raise SnapshotError("Same-game or future snapshot leakage blocked")
        if snap.get("production_modified") is not False or snap.get("calibrated") is not False:
            raise SnapshotError("Unexpected production/calibration flags")
    pid = str(player_id)
    candidates = [row for row in player_snapshot["rows"]
                  if row["TEAM"] == team and str(player_id_map.get((row["NAME"], row["TEAM"]), "")) == pid]
    if len(candidates) != 1:
        raise SnapshotError("Missing or ambiguous player ID mapping")
    teams = {row["TEAM"]: row for row in team_snapshot["rows"]}
    if len(teams) != len(team_snapshot["rows"]) or opponent not in teams or team not in teams:
        raise SnapshotError("Missing or duplicate matched team snapshot")
    player = candidates[0]
    own, opp = teams[team], teams[opponent]
    required_player = ("MpG", "USG%", "PpG", "RpG", "ApG")
    required_team = ("PACE", "oEFF", "dEFF")
    if any(player.get(k) is None for k in required_player):
        raise SnapshotError("Incomplete player baseline")
    if any(own.get(k) is None or opp.get(k) is None for k in required_team):
        raise SnapshotError("Incomplete team context")
    return {
        "status": "RESEARCH_ONLY_PREGAME_FEATURES",
        "player_id": pid,
        "event_date": game_day.isoformat(),
        "player_snapshot_as_of": player_snapshot["as_of"],
        "team_snapshot_as_of": team_snapshot["as_of"],
        "player_minutes_avg": player["MpG"],
        "player_usage_pct": player["USG%"],
        "player_points_avg": player["PpG"],
        "player_rebounds_avg": player["RpG"],
        "player_assists_avg": player["ApG"],
        "team_pace": own["PACE"],
        "opponent_pace": opp["PACE"],
        "opponent_defensive_efficiency": opp["dEFF"],
        "opponent_offensive_efficiency": opp["oEFF"],
        "opponent_defense_already_applied": False,
        "source_is_aggregate": True,
        "position_defense_verified": False,
        "production_modified": False,
        "calibrated": False,
    }

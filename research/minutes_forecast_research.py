"""Research-only pregame NBA minutes forecaster and chronological walk-forward evaluator.

Source: existing published player game logs (dates and observed minutes).
No sportsbook lines, retroactive prediction changes, injury assumptions or API calls.
The baseline is not promoted as a verified matchup-minute input without independent
prospective validation. Past actual MIN is never represented as current availability.
"""
import argparse
import json
from collections import Counter
from datetime import date, datetime, timezone
from math import isfinite
from pathlib import Path

MODEL_ID = "NBA_MINUTES_L5_SHRUNK_V1_RESEARCH"
MIN_HISTORY = 5
CANDIDATES = ("last3", "last5", "shrunk_last5")


def parse_logs(person, fields, before):
    """Fail closed on ambiguous, duplicated or post-cutoff player observations."""
    if not isinstance(fields, list) or "date" not in fields or "MIN" not in fields:
        raise ValueError("missing date/MIN schema")
    d_i, m_i = fields.index("date"), fields.index("MIN")
    if not isinstance(person.get("log"), list):
        raise ValueError("missing player game history")
    result = []
    seen = set()
    for record in person["log"]:
        if not isinstance(record, list) or len(record) <= max(d_i, m_i):
            raise ValueError("malformed game history")
        raw_day = record[d_i]
        try:
            played_day = date.fromisoformat(raw_day)
        except (TypeError, ValueError):
            raise ValueError("invalid game date") from None
        if raw_day in seen:
            raise ValueError("duplicate player game date")
        seen.add(raw_day)
        minutes = record[m_i]
        if type(minutes) not in (float, int) or not isfinite(minutes) or minutes < 0 or minutes > 60:
            raise ValueError("invalid observed minutes")
        if played_day >= before:
            raise ValueError("current or future game included in pregame snapshot")
        if minutes > 0:
            result.append((played_day, float(minutes)))
    result.sort(key=lambda x: x[0])
    return result


def predict(history, model="shrunk_last5"):
    """Predict next game minutes using prior played games; no postgame stats."""
    if model not in CANDIDATES or len(history) < MIN_HISTORY:
        raise ValueError("insufficient minutes history or unknown candidate")
    minutes = [float(x[1]) for x in history]
    if model == "last3":
        estimate = sum(minutes[-3:]) / 3
    elif model == "last5":
        estimate = sum(minutes[-5:]) / 5
    else:
        # Predeclared conservative shrinkage toward full known played-game baseline.
        estimate = 0.65 * sum(minutes[-5:]) / 5 + 0.35 * sum(minutes) / len(minutes)
    return round(max(0.0, min(48.0, estimate)), 2)


def evaluate(form):
    fields = form.get("log_fields")
    if not isinstance(fields, list) or "date" not in fields or "MIN" not in fields:
        raise ValueError("actual source lacks dated minute logs")
    sums = {k: 0.0 for k in CANDIDATES}
    sqs = {k: 0.0 for k in CANDIDATES}
    count = 0
    players = 0
    rejected = Counter()
    for p in form.get("players", []):
        try:
            # Read the full retrospectively available series, but each prediction
            # only uses observations preceding its own target date.
            hist = parse_logs(p, fields, date.max)
        except (ValueError, TypeError):
            rejected["unsafe_player_history"] += 1
            continue
        if len(hist) < MIN_HISTORY + 2:
            rejected["insufficient_chronological_samples"] += 1
            continue
        players += 1
        # Last few games are evaluated forward, with no random shuffle.
        start = max(MIN_HISTORY, len(hist) - 6)
        for idx in range(start, len(hist)):
            prior, actual = hist[:idx], hist[idx][1]
            for name in CANDIDATES:
                err = predict(prior, name) - actual
                sums[name] += abs(err)
                sqs[name] += err * err
            count += 1
    if not count:
        return {"status": "NO_ELIGIBLE_RETROSPECTIVE_SAMPLES",
                "samples": 0, "players": players,
                "production_approved": False, "rejections": dict(rejected)}
    errors = {key: {"mae": round(sums[key] / count, 3),
                    "rmse": round((sqs[key] / count) ** .5, 3)}
              for key in CANDIDATES}
    return {
        "status": "RETROSPECTIVE_TIME_ORDERED_MINUTES_RESEARCH",
        "model_id": MODEL_ID, "samples": count, "players": players,
        "candidate_metrics": errors,
        "research_model": "shrunk_last5",
        "best_retrospective_candidate": min(errors, key=lambda k: errors[k]["mae"]),
        "production_approved": False,
        "prospective_snapshot_validation": False,
        "uncertainty_calibrated": False,
        "rejections": dict(sorted(rejected.items())),
        "limitations": ("Retrospective minutes outcomes from a currently published "
                        "source; chronological historical splits avoid target leakage "
                        "but do not attest source publication before historic tipoffs. "
                        "No opponent adjustment, depth chart, teammate split or injury "
                        "minutes effects; no promotion without live frozen validation."),
    }


def prospective(form, evidence):
    """Attach a research-only minutes forecast to already timestamp-safe snapshots."""
    form_time = form.get("updated_at")
    freeze = evidence.get("captured_at")
    try:
        source_time = datetime.fromisoformat(form_time.replace("Z", "+00:00"))
        freeze_time = datetime.fromisoformat(freeze.replace("Z", "+00:00"))
        if source_time.tzinfo is None or freeze_time.tzinfo is None or source_time > freeze_time:
            raise ValueError("post-capture source")
    except (AttributeError, ValueError):
        raise ValueError("invalid pregame source provenance") from None
    if evidence.get("status") != "SOURCE_LINKED_PREGAME_RESEARCH_ONLY" or not evidence.get("future_games"):
        raise ValueError("invalid source-linked snapshot")
    fields = form.get("log_fields")
    by_id_team = {}
    for p in form.get("players", []):
        key = (str(p.get("player_id")), p.get("team"))
        if key in by_id_team:
            by_id_team[key] = None
        else:
            by_id_team[key] = p
    results = []
    missing = Counter()
    for record in evidence.get("research_players", []):
        player = by_id_team.get((record.get("player_id"), record.get("team")))
        if not player:
            missing["ambiguous_player_identity"] += 1
            continue
        try:
            target = date.fromisoformat(record["date_eastern"])
            prior = parse_logs(player, fields, target)
            prediction = predict(prior)
        except (ValueError, KeyError, TypeError):
            missing["missing_safe_minutes_history"] += 1
            continue
        # No injury OUT minute forecasts: a hard participation assumption would
        # silently turn an uncertainty into a playable prop.
        if str(record.get("injury_status", "")).lower() in ("out", "doubtful"):
            missing["officially_unavailable_or_doubtful"] += 1
            continue
        if not record.get("minutes_source") or record.get("minutes_source_published_at") != form_time:
            missing["source_mismatch"] += 1
            continue
        results.append({
            "game_id": record["game_id"], "player_id": record["player_id"],
            "team": record["team"], "opponent": record["opponent"],
            "start": record["start"], "captured_at": freeze,
            "predicted_minutes_research": prediction,
            "model_id": MODEL_ID, "source": record["minutes_source"],
            "source_published_at": form_time, "source_game_count": len(prior),
            "injury_status": record.get("injury_status", "UNKNOWN_NOT_LISTED"),
            "unknown_injury_status": record.get("injury_status") == "UNKNOWN_NOT_LISTED",
            "matchup_hit_estimate_eligible": False,
            "production_approved": False,
        })
    return {"status": "RESEARCH_MINUTES_ONLY", "captured_at": freeze,
            "model_id": MODEL_ID, "predictions": results,
            "prediction_count": len(results),
            "blockers": dict(sorted(missing.items())),
            "production_approved": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--form", default="docs/current_form.json")
    parser.add_argument("--evidence", default="pregame-evidence-research.json")
    parser.add_argument("--output", default="minutes-forecast-research.json")
    a = parser.parse_args()
    form = json.loads(Path(a.form).read_text())
    evidence = json.loads(Path(a.evidence).read_text())
    report = {"backtest": evaluate(form), "prospective": prospective(form, evidence)}
    Path(a.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "backtest_samples": report["backtest"].get("samples", 0),
        "retrospective_mae": report["backtest"].get("candidate_metrics", {}),
        "prospective_predictions": report["prospective"]["prediction_count"],
        "production_approved": False}, indent=2))


if __name__ == "__main__":
    main()

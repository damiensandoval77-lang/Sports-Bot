"""Fail-closed reliability checks for a normalized Sports-Bot status snapshot.

Input schema is documented in docs/reliability_guardrails.md. This is intentionally
separate from the production publisher until its exact output schema is wired in.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

UTC = dt.timezone.utc

def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be ISO-8601")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(UTC)

def validate(snapshot, now=None, max_age_minutes=90, max_grade_delay_hours=6):
    now = now or dt.datetime.now(UTC)
    errors = []
    warnings = []
    if not isinstance(snapshot, dict):
        return ["snapshot must be an object"], []
    for key in ("generated_at", "expected_game_ids", "games", "cards"):
        if key not in snapshot:
            errors.append("missing required field: " + key)
    if errors:
        return errors, warnings
    try:
        age = (now - parse_time(snapshot["generated_at"])).total_seconds() / 60
        if age > max_age_minutes:
            errors.append("snapshot stale: %.1f minutes" % age)
        if age < -5:
            errors.append("snapshot timestamp is in the future")
    except (TypeError, ValueError) as exc:
        errors.append("invalid generated_at: " + str(exc))

    expected = snapshot["expected_game_ids"]
    games = snapshot["games"]
    cards = snapshot["cards"]
    if not isinstance(expected, list) or not isinstance(games, list) or not isinstance(cards, list):
        errors.append("expected_game_ids, games, and cards must be arrays")
        return errors, warnings
    if len(expected) != len(set(map(str, expected))):
        errors.append("duplicate expected game IDs")
    if not expected:
        errors.append("expected schedule is empty (cannot assert coverage)")
    ids = [str(g.get("id")) for g in games if isinstance(g, dict)]
    if len(ids) != len(games) or len(ids) != len(set(ids)):
        errors.append("invalid or duplicate game entries")
    missing = set(map(str, expected)) - set(ids)
    if missing:
        errors.append("missing scheduled games: " + ", ".join(sorted(missing)))
    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            errors.append("card %d not an object" % i)
            continue
        label = str(card.get("id", i))
        line = card.get("line")
        estimate = card.get("projection")
        lean = card.get("lean")
        probability = card.get("probability")
        if line is not None and (not isinstance(line, (int, float)) or isinstance(line, bool)):
            errors.append("card %s has invalid line" % label)
        if estimate is None:
            if lean is not None or probability is not None:
                errors.append("card %s has invented lean/probability without a projection" % label)
        else:
            if not isinstance(estimate, (int, float)) or isinstance(estimate, bool):
                errors.append("card %s has invalid projection" % label)
            if line is None:
                warnings.append("card %s has projection but no provider line" % label)
            if lean not in ("OVER", "UNDER", "PUSH", None):
                errors.append("card %s has unrecognized lean" % label)
            if probability is not None and (not isinstance(probability, (int, float)) or isinstance(probability, bool) or not 0 <= probability <= 1):
                errors.append("card %s has invalid probability (expected 0..1)" % label)

    for game in games:
        if not isinstance(game, dict):
            continue
        if game.get("status") != "final":
            continue
        if game.get("ungraded_predictions", 0) <= 0:
            continue
        try:
            hours = (now - parse_time(game["final_at"])).total_seconds() / 3600
            if hours >= max_grade_delay_hours:
                errors.append("final game %s has %s predictions ungraded after %.1f h" %
                              (game.get("id"), game["ungraded_predictions"], hours))
        except (KeyError, TypeError, ValueError):
            errors.append("final game %s missing valid final_at" % game.get("id"))
    return errors, warnings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--max-age-minutes", type=int, default=90)
    parser.add_argument("--max-grade-delay-hours", type=int, default=6)
    args = parser.parse_args()
    try:
        data = json.loads(args.snapshot.read_text(encoding="utf-8"))
        errors, warnings = validate(data, max_age_minutes=args.max_age_minutes,
                                    max_grade_delay_hours=args.max_grade_delay_hours)
    except (OSError, ValueError) as exc:
        print("FAIL:", exc)
        return 2
    for item in warnings:
        print("WARN:", item)
    for item in errors:
        print("FAIL:", item)
    if errors:
        return 1
    print("PASS: schedule coverage, freshness, card integrity, and grading lag")
    return 0

if __name__ == "__main__":
    sys.exit(main())

"""Read-only eligibility audit for the future matchup-aware Hit Estimate.

Checks ACTUAL frozen ledger records against as-of source availability. Never
backfills model inputs from subsequently published form, injury or schedule files.
No betting-provider requests, predictions, grading, production writes, or API keys.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from research.matchup_hit_estimate import REQUIRED


def moment(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def audit(ledger, form):
    rows = ledger.get("records", [])
    if ledger.get("status") != "FROZEN_NEW_AI_ALL_MARKET" or not isinstance(rows, list):
        raise ValueError("unexpected immutable ledger schema")
    updated = moment(form.get("updated_at"))
    causes = Counter()
    by_market = Counter()
    eligible = 0
    for record in rows:
        stat = record.get("stat", "UNKNOWN")
        by_market[stat] += 1
        captured = moment(record.get("captured_at"))
        start = moment(record.get("start"))
        if not captured or not start or captured >= start:
            causes["invalid_pretip_freeze"] += 1
            continue
        # Feed snapshots created after the actual capture cannot be asserted
        # as information the pick/model had when it was frozen.
        if not updated or updated > captured:
            causes["current_form_not_proven_available_at_capture"] += 1
        factors = record.get("matchup_factors")
        if not isinstance(factors, dict):
            causes["no_frozen_matchup_factor_snapshot"] += 1
            continue
        valid = True
        for name in REQUIRED:
            item = factors.get(name)
            if not isinstance(item, dict) or not item.get("source"):
                causes["missing_" + name] += 1
                valid = False
                continue
            observed = moment(item.get("observed_at"))
            # 'observed_at' is when data was available to the actual pick,
            # not an inferred historical NBA game date.
            if observed is None or observed > captured:
                causes["not_asof_" + name] += 1
                valid = False
            baseline, matchup = item.get("baseline"), item.get("matchup")
            for number in (baseline, matchup):
                if (isinstance(number, bool) or not isinstance(number, (int, float))
                        or not (0 < number < float("inf"))):
                    causes["invalid_ratio_" + name] += 1
                    valid = False
                    break
        if valid:
            eligible += 1
    # Eligibility requires a validated immutable feature snapshot.
    # Form's published timestamp is reported as a separate contextual
    # disqualifier for *using this particular file* as contemporaneous input.
    return {
        "status": "RESEARCH_ELIGIBILITY_AUDIT",
        "production_promotion_approved": False,
        "input_ledger_records": len(rows),
        "frozen_matchup_records_eligible": eligible,
        "frozen_matchup_records_unverified": len(rows) - eligible,
        "markets": dict(sorted(by_market.items())),
        "blocker_counts": dict(sorted(causes.items())),
        "current_form_updated_at": form.get("updated_at"),
        "interpretation": (
            "Reports whether each original frozen record contains six independently "
            "source-linked and capture-time-safe matchup features. Current form "
            "publication time cannot prove older values were known pretip. "
            "No Hit Estimate is recomputed or changed."
        ),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", default="docs/lagged_matchup_all_market_ledger.json")
    p.add_argument("--form", default="docs/current_form.json")
    p.add_argument("--output")
    args = p.parse_args()
    result = audit(json.loads(Path(args.ledger).read_text()),
                   json.loads(Path(args.form).read_text()))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()

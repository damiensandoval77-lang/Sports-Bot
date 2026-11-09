# Sports-Bot reliability guardrails (staged, not deployed)

This change adds an **independent, fail-closed validator** and tests. It does **not**
yet read the production website's internal data or automatically repair feeds.
Connect the publisher's actual schema to the normalized input below before making
this a required deployment gate. Do not interpret passing unit tests as live-site uptime.

## Normalized snapshot

Generate one UTF-8 JSON file per publishing run. Example:

```json
{
  "generated_at": "2026-11-09T22:50:00Z",
  "expected_game_ids": ["nba-001"],
  "games": [{"id": "nba-001", "status": "live"}],
  "cards": [
    {"id": "player-points", "line": 22.5, "projection": 25.1,
     "lean": "OVER", "probability": 0.63},
    {"id": "player-rebounds", "line": 8.5, "projection": null,
     "lean": null, "probability": null}
  ]
}
```

`expected_game_ids` **must** be generated independently from the authoritative
schedule. Never derive expected IDs from the rendered cards or a potentially
partial prop feed. A missing projection is valid only when lean and probability
are also absent. Probabilities use 0–1 units.

For each final game, include `final_at` and `ungraded_predictions`.
The validator fails when unresolved grading exceeds the grace period.
Game IDs and card IDs should remain stable for auditability.

## Run

```bash
python -m unittest iphone_bot.tests.test_reliability_guardrails -v
python iphone_bot/reliability_guardrails.py path/to/normalized_snapshot.json
```

Exit code 0 means checks passed; nonzero should block publishing the snapshot.
Failure must preserve the previous verified snapshot, clearly mark it stale,
and alert operators; **never replace valid data with blank pages**.

## Follow-up integration requirements

1. Map actual schedule, card, and grading exports into this normalized JSON.
2. Run before atomic publish; retain last-good data and timestamp.
3. Show degraded provider status and unavailable projections without fabricating values.
4. Alert after two consecutive refresh failures; log reason and snapshot age.
5. Check production iPhone browser after deploy and report card counts and JS errors.
6. Test failed provider, stale snapshot, empty schedule, missing games, and late grading in CI.

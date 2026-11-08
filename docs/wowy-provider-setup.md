# WOWY / lineup impact provider setup (step 1)

**Current state: connector is staged, but no PBP Stats API requests are made and no real on/off rows are imported.** Never interpret the API's public documentation as a license to use the API or its data for an NBA prop/betting product.

## Exact endpoints confirmed in public provider documentation
- API reference: https://api.pbpstats.com/docs
- Provider's code examples: https://github.com/dblackrun/pbpstats-api-code-examples
- `GET https://api.pbpstats.com/get-wowy-stats/nba` (provider examples use `Type=Player`, `Season=2026-27`, `SeasonType=Regular Season`, `TeamId`, `0Exactly1OnFloor=PLAYER_ID`, and `1Exactly1OnFloor=TEAMMATE_ID` or `1Exactly1OffFloor=TEAMMATE_ID`).
- `GET https://api.pbpstats.com/get-on-off/nba/player` (documented player on/off data).
- `GET https://api.pbpstats.com/get-playing-time-distribution/nba` (documented distributions).

`iphone_bot/pbpstats_request_plan.py` only constructs the parameters; it never performs HTTP. These endpoints and their response schemas should be revisited with the provider before production use. Full-season provider totals must **never** be used as if known before an earlier game. Ask the provider about supported game-date filtering, data availability timestamps, and access quotas.

## Outstanding provider questions
1. Does the provider permit automated access by an individual NBA player-prop research/betting-oriented application? Does it cover model training/research or only personal site viewing?
2. What are the access requirements, plans, cost, rate limits, and 2026-27 refresh latency?
3. Can responses be filtered by a strict *historical game cutoff* rather than current full-season aggregates?
4. Does the provider permit local caching of observations, private derived predictions, or public redistribution of any aggregate data?
5. What do `multi_row_table_data` and the individual per-player rows contain in the permitted plan? How are player on-floor minutes and games represented?
6. Is an API key needed, and where can it be stored securely (never in a public repository or browser JS)?

## After explicit provider permission is confirmed
Prepare an authorization note that documents permission for `NBA_PROP_RESEARCH`. Keep it private, not in GitHub. Example private `approval.json`:
```json
{
  "reviewed_for_betting_analytics": true,
  "allowed_use": "NBA_PROP_RESEARCH",
  "reviewer_confirmation": "MANUALLY_VERIFIED",
  "permission_reference": "REPLACE_WITH_REAL_DOCUMENTED_PERMISSION"
}
```
Do not set the manifest to verified unless written terms/permissions support this usage. **This manifest records a human-reviewed determination; software cannot prove legal permission.**

Prepare a **normalized** provider export `export.json` after confirming the endpoint, mapping and lawful data usage. This is a *fictional schema example*, not actual PBP Stats response data:
```json
{
  "source": "AUTHORIZED_PROVIDER_NAME",
  "season": "2026-27",
  "generated_at": "2026-11-07T18:00:00Z",
  "observations": [{
    "player_id": "100",
    "teammate_id": "900",
    "team": "BOS",
    "data_through": "2026-11-06",
    "observed_through_at": "2026-11-07T17:00:00Z",
    "with": {
      "games": 7, "minutes": 180,
      "PTS_per36": 20.0, "REB_per36": 6.0, "AST_per36": 4.0
    },
    "without": {
      "games": 7, "minutes": 160,
      "PTS_per36": 24.0, "REB_per36": 7.0, "AST_per36": 6.0
    }
  }]
}
```
Values and IDs above are examples **only**. Use exact active-season NBA player IDs from `docs/current_form.json`. Observe `data_through` and `observed_through_at` cutoffs. Both sample groups require at least 5 games and 120 minutes. Only official same-game OUT players can activate the on/off shadow. The existing immutable pretip snapshot and same-line postgame grading still apply.

Run locally:
```bash
python -m iphone_bot.import_authorized_onoff --export /secure/export.json --approval /secure/approval.json
python -m unittest discover -s iphone_bot/tests -p 'test_import_authorized_onoff.py' -v
python -m unittest discover -s iphone_bot/tests -p 'test_lineup_onoff_research.py' -v
```
The importer validates exact player/team IDs against `docs/current_form.json` and writes only to the ignored `data/nba/private/lineup_onoff_research.json`. Never commit these licensed rows or approval papers, or place them in GitHub Pages. The pregame research script checks the private feed if available; the publicly committed `docs/lineup_onoff_research.json` remains empty/disabled.

**CI caveat:** GitHub Actions runners won't see private local files. Authorized automated deployment would require a permitted server-side source and secure secrets/authorization, implemented separately after permission is established. An ordinary workflow run will not generate licensed on/off projections yet.

## Research-only safety
- Neither source availability nor a teammate's absence proves a causal effect.
- A fixed cautious adjustment is only a challenger until independently graded on future games.
- No current simulated confidence, sportsbook quote or previously frozen forecast is overwritten by this source.

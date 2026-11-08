# WOWY / lineup impact provider setup (step 1)

**Current state: connector is staged, but no PBP Stats API requests are made and no real on/off rows are imported.** Never interpret the API's public documentation as a license to use the API or its data for an NBA prop/betting product.

## Exact endpoints confirmed in public provider documentation
- API reference: https://api.pbpstats.com/docs
- Provider's code examples: https://github.com/dblackrun/pbpstats-api-code-examples
- `GET https://api.pbpstats.com/get-wowy-stats/nba` (provider examples use `Type=Player`, `Season=2026-27`, `SeasonType=Regular Season`, `TeamId`, `0Exactly1OnFloor=PLAYER_ID`, and `1Exactly1OnFloor=TEAMMATE_ID` or `1Exactly1OffFloor=TEAMMATE_ID`).
- The provider's published OpenAPI specification also explicitly supports `FromDate` and `ToDate` (YYYY-MM-DD) on the WOWY endpoint: https://api.pbpstats.com/openapi.json. Our planner can now supply both, with `ToDate` no later than the previous completed game day.
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

## Verified API response mapping checkpoint

- GitHub's 2026-11-07 one-shot test reached the API (HTTP 200, full JSON). The API returned `multi_row_table_data` rows containing `EntityId`, `Points`, `Rebounds`, `Assists`, `Minutes`, and `SecondsPlayed`. Those fields were identified by field name only; raw third-party values are not stored publicly.
- New pure adapter: `iphone_bot/pbpstats_wowy_adapter.py`. It selects one exact `EntityId` in each ON/OFF response and computes PTS/REB/AST per-36 minutes using provider totals and exposure time.
- The adapter additionally requires **independently verified game dates for each split**, a source observation timestamp, and matching season/team/teammate IDs. An aggregate API response alone is insufficient evidence of the number of independent games.
- See `iphone_bot/pbpstats_request_plan.py` for pregame date-bounded request parameters. Current full-season totals after an event must not be used to simulate what was known at that event.
- Tests use fictional provider-shaped dictionaries, not a permissioned production data feed.

### Outstanding before actual automated ingestion

1. Confirm whether the API permits recurring automated usage in a betting-prop research service, local retention, and derived forecasts.
2. Verify actual 2026-27 request parameters and complete ON/OFF response semantics for each targeted pair, including which game-date summaries correspond to each split.
3. Provide real independent, date-stamped game coverage for both groups and preserve pretip cutoff provenance.
4. Set up secure server-side permitted ingestion; the GitHub Actions test makes a *single historical connectivity probe*, not routine data ingestion.

## End-to-end offline response assembly (now implemented)

The adapter and local validator are connected by `iphone_bot/assemble_pbpstats_wowy.py`. No network request occurs during assembly. Provide a private `bundle.json` containing independently authorized/obtained responses; both responses must be generated by the **documented date-limited requests** and each must include separately independently verified completed game dates.

```bash
python -m iphone_bot.assemble_pbpstats_wowy \
  --bundle /secure/bundle.json \
  --approval /secure/approval.json
python -m unittest discover -s iphone_bot/tests -p 'test_assemble_pbpstats_wowy.py' -v
```

The `bundle.json` contract is `{season,source,generated_at,pairs:[...]}`. Each pair contains `player_id`, `teammate_id`, `team`, `data_through`, `observed_through_at`, `with_response`, `without_response`, `with_provenance`, `without_provenance`. Both provenance objects contain `verified_completed_games: true`, an actual `game_dates` list, and **exact original `request_params` including `FromDate`/`ToDate`**. Supplying arbitrary game dates or marking a self-created list verified does not establish real coverage; date lists must be independently derived from the underlying source possessions/verified game records. The workflow never invents them.

Raw `with_response` and `without_response` must contain the provider's `multi_row_table_data` with an unambiguous `EntityId` equal to the subject's NBA ID and numeric `Points`, `Rebounds`, `Assists`, and exposure minutes. If data rights, independent coverage, cutoff or sampling units are uncertain, the import must be rejected and the production model remains unchanged.

**Important:** A GitHub Actions HTTP 200 is evidence of reachable public transport, not a grant of rights for ongoing betting-model analytics, training, caching, or redistribution. The permitted-use issue remains open. The provider's exact 2026-27 on/off response semantics and games-per-split provenance are not independently verified yet.

## Verified game-level possession overlap gate (new)

The public PBP Stats API advertises `get-playing-time-distribution/nba` and `get-wowy-combo-playing-time-distribution/nba`; the former's official notebook shows `GameId`, `Date`, and per-possession `StartTime`/`EndTime`. Those possession/stint records are suitable for inspecting which teammates shared playing time, subject to source permission and correct game-elapsed time semantics.

New module `iphone_bot/pbpstats_game_coverage.py` computes per-game exact intersection between the target's and teammate's on-floor intervals. It requires unambiguous 10-digit GameIds and dates strictly before the target game's pretip date, rejects duplicated or overlapping possession intervals, separately counts ON/OFF game dates and minutes, and demands at least 5 distinct games and 120 minutes in each condition. No per-game stats are manufactured from an aggregate.

The offline assembler `iphone_bot/assemble_pbpstats_wowy.py` now requires private `target_distribution` and `teammate_distribution` lists in every pair, compares the independently computed ON/OFF game dates to the provider query provenance, and reconciles observed ON/OFF minutes with the corresponding WOWY API aggregate to within 3% or 3 minutes. If the distributions cannot be obtained or do not reconcile, no licensed feed is accepted.

This test path is integrated into the GitHub workflows with synthetic game-level interval fixtures; it does **not** mean the actual 2026–27 distributions have been verified. The API's published examples contain historical response examples; permission, current-season source behavior and ON/OFF possession timing still require confirmation.

## Provider licensing inquiry

`docs/pbpstats-permission-inquiry.md` contains a draft asking the provider to confirm use in a sportsbook/PrizePicks analytics workflow, caching, paid tiers, and third-party NBA rights. The draft is **not sent** and does not grant permission.

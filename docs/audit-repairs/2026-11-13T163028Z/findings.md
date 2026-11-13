# Sports-Bot repair cycle — PARTIAL

Started 2026-11-13 16:30:28 UTC. Nine newly diagnosed defect groups patched in six merged PRs. Hosted recovery completed at 17:30:47 UTC: 90 requested finals verified, no rejected games. Eight defect groups have independent hosted/public execution evidence; D9 is configuration-verified only.

## Repair log

### D1 — high — PR #417
Public monitor kept an obsolete failure after a successful publisher.
Root cause: Missing publisher completion trigger and transient public fetch failures.
Change: Recheck successful main publisher; retain bounded retry evidence.
Verification: PUBLIC_JSON_VERIFIED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/417); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/71d6dbcf96df2a1c5ee373d2cfe46b6469b36a44).
Files: `.github/workflows/verify_public_dashboard.yml`, `iphone_bot/tests/test_verify_deployed_dashboard.py`, `iphone_bot/verify_deployed_dashboard.py`
Runs: [43467902657](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467902657), [43467947980](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467947980)

### D2 — high — PR #418
Valid final boxes rejected when official rows included DNPs.
Root cause: DNP rows incorrectly participated in played-player validation.
Change: Exclude explained zero-minute DNP rows; reject contradictory totals or missing reasons.
Verification: HOSTED_RECOVERY_VERIFIED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/418); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/f86be1a049c113dd5580f349143249ebec89f2da).
Files: `research/tests/test_official_defense_backfill.py`, `research/tests/test_verified_team_defense_context.py`, `research/verified_team_defense_context.py`
Runs: [43467057380](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467057380)

### D3 — high — PR #419
Official-history collector returned no verified games during schedule outage.
Root cause: Official event discovery depended on unavailable live schedule.
Change: Use saved genuine ID/date/team hints; independently verify every final box.
Verification: HOSTED_RECOVERY_VERIFIED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/419); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/77efc770fab0eb3c4e786e7e9c8e694b29f9ece2).
Files: `.github/workflows/research-official-defense-history.yml`, `research/data/official_nba_schedule_hints_2026_27.json`, `research/official_defense_backfill.py`, `research/tests/test_official_defense_backfill.py`
Runs: [43467057380](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467057380)

### D4 — medium — PR #420
Privileged comparison publisher and monitor used mutable action tags.
Root cause: Write-capable jobs did not pin dependency revisions.
Change: Pin checkout and Python setup to verified commit SHAs.
Verification: HOSTED_EXECUTION_VERIFIED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/420); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/68cce8cce70eafc7a95eda058bef6c04601867fb).
Files: `.github/workflows/publish_live_pp_ai_join.yml`, `.github/workflows/verify_public_dashboard.yml`
Runs: [43467902657](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467902657), [43467947980](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467947980)

### D5 — high — PR #421
Complete ATL-IND final rejected because Indiana played only six players.
Root cause: Seven-player minimum incorrectly excluded a real complete rotation.
Change: Allow five/six only with exact official minutes totaling regulation/OT duration and all existing identity/score checks.
Verification: HOSTED_RECOVERY_VERIFIED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/421); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/15d748de2d320a4bd97a3b62186ccd068950a4ad).
Files: `.github/workflows/research-official-defense-history.yml`, `research/official_defense_backfill.py`, `research/tests/test_official_defense_backfill.py`, `research/tests/test_verified_team_defense_context.py`, `research/verified_team_defense_context.py`
Runs: [43468528082](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43468528082)

### D6 — medium — PR #421
Offline PR checks queued behind slow production history collection.
Root cause: PR and production jobs shared a concurrency group.
Change: Isolate PR concurrency by PR number, preserve production serialization.
Verification: HOSTED_CONCURRENCY_VERIFIED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/421); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/15d748de2d320a4bd97a3b62186ccd068950a4ad).
Files: `.github/workflows/research-official-defense-history.yml`, `research/official_defense_backfill.py`, `research/tests/test_official_defense_backfill.py`, `research/tests/test_verified_team_defense_context.py`, `research/verified_team_defense_context.py`
Runs: [43468126664](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43468126664), [43468126456](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43468126456), [43468126276](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43468126276)

### D7 — high — PR #423
Legacy collectors could spend Odds API credits when triggered.
Root cause: No default-off guard before network requests.
Change: Require explicit opt-in; preserve old observation timestamps; publish disabled status.
Verification: PUBLIC_JSON_VERIFIED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/423); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/9c6133d32d827b5992b02f62ebf6133977b8622e).
Files: `.github/workflows/hide-tipped-ai-props-tests.yml`, `.github/workflows/nba-consensus-test.yml`, `.github/workflows/nba-live-tracker-external-verification.yml`, `.github/workflows/nba-slate-resilience-tests.yml`, `.github/workflows/nba-ui-integrity.yml`, `.github/workflows/opponent_simulation_tests.yml`, `.github/workflows/verify-live-tracker-espn.yml`, `iphone_bot/fetch_game_moneylines.py`, `iphone_bot/fetch_odds_scores.py`, `iphone_bot/fetch_props.py`, `iphone_bot/tests/test_fetch_props.py`, `iphone_bot/tests/test_paid_odds_disabled.py`, `iphone_bot/tests/test_root_redirect.cjs`
Runs: [43470362958](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43470362958)

### D8 — high — PR #423
Legacy UI CI failed against the retired root dashboard.
Root cause: Tests still required old widgets, old timer, and simulation labels.
Change: Run canonical unified app/root redirect contracts while retaining backend tests.
Verification: HOSTED_CI_AND_PRODUCTION_VERIFIED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/423); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/9c6133d32d827b5992b02f62ebf6133977b8622e).
Files: `.github/workflows/hide-tipped-ai-props-tests.yml`, `.github/workflows/nba-consensus-test.yml`, `.github/workflows/nba-live-tracker-external-verification.yml`, `.github/workflows/nba-slate-resilience-tests.yml`, `.github/workflows/nba-ui-integrity.yml`, `.github/workflows/opponent_simulation_tests.yml`, `.github/workflows/verify-live-tracker-espn.yml`, `iphone_bot/fetch_game_moneylines.py`, `iphone_bot/fetch_odds_scores.py`, `iphone_bot/fetch_props.py`, `iphone_bot/tests/test_fetch_props.py`, `iphone_bot/tests/test_paid_odds_disabled.py`, `iphone_bot/tests/test_root_redirect.cjs`
Runs: [43469958544](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958544), [43469958884](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958884), [43469958870](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958870), [43469958546](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958546), [43469958631](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958631), [43469958488](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958488), [43470363267](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43470363267), [43470363196](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43470363196), [43470363163](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43470363163)

### D9 — medium — PR #423
Obsolete external tracker workflow still targeted Replit.
Root cause: Retired service remained a runnable health probe.
Change: Make workflow manual-only retirement notice, remove external requests.
Verification: CONFIGURATION_VERIFIED_NOT_EXECUTED. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/423); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/9c6133d32d827b5992b02f62ebf6133977b8622e).
Files: `.github/workflows/hide-tipped-ai-props-tests.yml`, `.github/workflows/nba-consensus-test.yml`, `.github/workflows/nba-live-tracker-external-verification.yml`, `.github/workflows/nba-slate-resilience-tests.yml`, `.github/workflows/nba-ui-integrity.yml`, `.github/workflows/opponent_simulation_tests.yml`, `.github/workflows/verify-live-tracker-espn.yml`, `iphone_bot/fetch_game_moneylines.py`, `iphone_bot/fetch_odds_scores.py`, `iphone_bot/fetch_props.py`, `iphone_bot/tests/test_fetch_props.py`, `iphone_bot/tests/test_paid_odds_disabled.py`, `iphone_bot/tests/test_root_redirect.cjs`
Runs: 

## Full workflow and branch evidence

[Every tracked workflow, triggers, latest observed run and exceptions](workflows.md). Machine-readable workflow inventory and run history are compressed alongside this receipt. Both initial and final advertised branch/PR-tip ancestry inventories are retained. No claim is made that every historical revision was executed.

## Remaining blockers

- **B1 (high):** Six players have only 3-7 qualifying same-team opportunity-history games; primary requires 8. Preserve explicit unavailable state; cannot invent history or promote unvalidated research estimates.
- **B2 (high):** Transient PrizePicks freshness warning recovered by existing scheduled publication at 17:19:22 UTC. No paid refresh was initiated by this audit; source readiness READY on final readback.
- **B3 (high):** Legacy branch Pages deployment cancellations and races. Repository owner must select Settings > Pages > Build and deployment > Source > GitHub Actions; connector cannot change setting and browser lacks authenticated admin session.
- **B4 (medium):** No complete 72-hour clean production window or active-game verification during this run. Do not force release gate green; requires actual future observations.
- **B5 (medium):** 396 remaining mutable action references and incomplete historical runtime evidence. Recorded as supply-chain/coverage limitations, not 396 proven exploited vulnerabilities. Bulk workflow changes can activate prohibited paid collectors; no indiscriminate trigger..

## Grading and public verification

See `receipt.json`, `capture-coverage.json`, `nightly-grading.json`, `nfl-grading.json`, `iphone-deployed.json`, `deployment-convergence.json`, and the hosted phone artifact. Recovered final box scores are research observations captured now and never retroactive pretip evidence.

Evidence window ended 2026-11-13T17:33:28.177005+00:00; duration 3780 seconds. Final sampled main before receipt: `c27954440370d56635377ebbbc12081c5cbec200`.

Final required readiness: 9/10. Current primary coverage: 355/371 standard offers; 16 missing. Saved quote coverage: 607 quotes, 28 thresholds without primary models (12 separate research receipts, 16 no AI receipt). Frozen line-backed future predictions: 582.

The hosted 90-game research window still has two insufficient-prior-defense contexts. The separately recovered 91-game cache supplies all 14 contexts, but is not promoted into production predictions.

Eight defect groups have independent public/hosted execution evidence. Retiring the obsolete external tracker is verified in merged workflow configuration only; it was not dispatched because the available connector has no workflow-dispatch operation.

Requested: notify Damien through enabled ChatGPT mobile notifications. Delivery is not confirmed.

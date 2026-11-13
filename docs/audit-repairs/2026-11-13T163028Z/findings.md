# Sports-Bot repair cycle — PARTIAL

10 newly diagnosed defect groups patched across seven merged PRs; nine have independent public or hosted execution evidence. D9 is configuration-only verification. Overall production remains 9/10 required checks.

Started 2026-11-13T16:30:28Z; evidence collection ended 2026-11-13T17:50:31.116634+00:00; 4803 seconds. Initial main `ecf0cf06c89af8608c5f02ab718970a7ce764637`; final static-verified main `94c48fec955c3bc11a5760e2773f373a2b648919`. Public release `dp-public-qa-labels-20261113-r36`.

## Complete findings and repair log

### D1 — high — PR #417
Public monitor kept an obsolete failure after a successful publisher.
Root cause: Missing publisher completion trigger and transient public fetch failures.
Change: Recheck successful main publisher; retain bounded retry evidence.
Verification: **PUBLIC_JSON_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/417); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/71d6dbcf96df2a1c5ee373d2cfe46b6469b36a44).
Files: `.github/workflows/verify_public_dashboard.yml`, `iphone_bot/tests/test_verify_deployed_dashboard.py`, `iphone_bot/verify_deployed_dashboard.py`
Runs: [43467902657](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467902657), [43467947980](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467947980)

### D2 — high — PR #418
Valid final boxes rejected when official rows included DNPs.
Root cause: DNP rows incorrectly participated in played-player validation.
Change: Exclude explained zero-minute DNP rows; reject contradictory totals or missing reasons.
Verification: **HOSTED_RECOVERY_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/418); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/f86be1a049c113dd5580f349143249ebec89f2da).
Files: `research/tests/test_official_defense_backfill.py`, `research/tests/test_verified_team_defense_context.py`, `research/verified_team_defense_context.py`
Runs: [43467057380](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467057380)

### D3 — high — PR #419
Official-history collector returned no verified games during schedule outage.
Root cause: Official event discovery depended on unavailable live schedule.
Change: Use saved genuine ID/date/team hints; independently verify every final box.
Verification: **HOSTED_RECOVERY_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/419); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/77efc770fab0eb3c4e786e7e9c8e694b29f9ece2).
Files: `.github/workflows/research-official-defense-history.yml`, `research/data/official_nba_schedule_hints_2026_27.json`, `research/official_defense_backfill.py`, `research/tests/test_official_defense_backfill.py`
Runs: [43467057380](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467057380)

### D4 — medium — PR #420
Privileged comparison publisher and monitor used mutable action tags.
Root cause: Write-capable jobs did not pin dependency revisions.
Change: Pin checkout and Python setup to verified commit SHAs.
Verification: **HOSTED_EXECUTION_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/420); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/68cce8cce70eafc7a95eda058bef6c04601867fb).
Files: `.github/workflows/publish_live_pp_ai_join.yml`, `.github/workflows/verify_public_dashboard.yml`
Runs: [43467902657](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467902657), [43467947980](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43467947980)

### D5 — high — PR #421
Complete ATL-IND final rejected because Indiana played only six players.
Root cause: Seven-player minimum incorrectly excluded a real complete rotation.
Change: Allow five/six only with exact official minutes totaling regulation/OT duration and all existing identity/score checks.
Verification: **HOSTED_RECOVERY_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/421); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/15d748de2d320a4bd97a3b62186ccd068950a4ad).
Files: `.github/workflows/research-official-defense-history.yml`, `research/official_defense_backfill.py`, `research/tests/test_official_defense_backfill.py`, `research/tests/test_verified_team_defense_context.py`, `research/verified_team_defense_context.py`
Runs: [43468528082](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43468528082)

### D6 — medium — PR #421
Offline PR checks queued behind slow production history collection.
Root cause: PR and production jobs shared a concurrency group.
Change: Isolate PR concurrency by PR number, preserve production serialization.
Verification: **HOSTED_CONCURRENCY_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/421); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/15d748de2d320a4bd97a3b62186ccd068950a4ad).
Files: `.github/workflows/research-official-defense-history.yml`, `research/official_defense_backfill.py`, `research/tests/test_official_defense_backfill.py`, `research/tests/test_verified_team_defense_context.py`, `research/verified_team_defense_context.py`
Runs: [43468126664](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43468126664), [43468126456](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43468126456), [43468126276](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43468126276)

### D7 — high — PR #423
Legacy collectors could spend Odds API credits when triggered.
Root cause: No default-off guard before network requests.
Change: Require explicit opt-in; preserve old observation timestamps; publish disabled status.
Verification: **PUBLIC_JSON_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/423); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/9c6133d32d827b5992b02f62ebf6133977b8622e).
Files: `.github/workflows/hide-tipped-ai-props-tests.yml`, `.github/workflows/nba-consensus-test.yml`, `.github/workflows/nba-live-tracker-external-verification.yml`, `.github/workflows/nba-slate-resilience-tests.yml`, `.github/workflows/nba-ui-integrity.yml`, `.github/workflows/opponent_simulation_tests.yml`, `.github/workflows/verify-live-tracker-espn.yml`, `iphone_bot/fetch_game_moneylines.py`, `iphone_bot/fetch_odds_scores.py`, `iphone_bot/fetch_props.py`, `iphone_bot/tests/test_fetch_props.py`, `iphone_bot/tests/test_paid_odds_disabled.py`, `iphone_bot/tests/test_root_redirect.cjs`
Runs: [43470362958](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43470362958)

### D8 — high — PR #423
Legacy UI CI failed against the retired root dashboard.
Root cause: Tests still required old widgets, old timer, and simulation labels.
Change: Run canonical unified app/root redirect contracts while retaining backend tests; follow-up PR424 replaces remaining obsolete test entry points with canonical app/live/redirect behavior and fixes their triggers..
Verification: **HOSTED_CI_AND_PRODUCTION_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/423); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/9c6133d32d827b5992b02f62ebf6133977b8622e).
Files: `.github/workflows/hide-tipped-ai-props-tests.yml`, `.github/workflows/nba-consensus-test.yml`, `.github/workflows/nba-live-tracker-external-verification.yml`, `.github/workflows/nba-slate-resilience-tests.yml`, `.github/workflows/nba-ui-integrity.yml`, `.github/workflows/opponent_simulation_tests.yml`, `.github/workflows/verify-live-tracker-espn.yml`, `iphone_bot/fetch_game_moneylines.py`, `iphone_bot/fetch_odds_scores.py`, `iphone_bot/fetch_props.py`, `iphone_bot/tests/test_fetch_props.py`, `iphone_bot/tests/test_paid_odds_disabled.py`, `iphone_bot/tests/test_root_redirect.cjs`
Runs: [43469958544](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958544), [43469958884](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958884), [43469958870](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958870), [43469958546](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958546), [43469958631](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958631), [43469958488](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43469958488), [43470363267](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43470363267), [43470363196](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43470363196), [43470363163](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43470363163), [43475664150](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43475664150), [43475664064](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43475664064), [43475663741](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43475663741), [43476030403](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43476030403), [43476030315](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43476030315), [43476030003](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43476030003)
Additional merged repair: [PR424](https://github.com/damiensandoval77-lang/Sports-Bot/pull/424). All three corrected entry points passed production push runs after PR424 merged.
Additional files: `.github/workflows/nfl-ui-smoke.yml`, `.github/workflows/phase1_dashboard_scoreboard.yml`, `.github/workflows/phase1_real_pp_join.yml`, `tests/test_nfl_player_cards.cjs`, `iphone_bot/tests/test_dashboard_scoreboard_integration.py`, `iphone_bot/tests/test_real_prizepicks_pregame_join.cjs`

### D9 — medium — PR #423
Obsolete external tracker workflow still targeted Replit.
Root cause: Retired service remained a runnable health probe.
Change: Make workflow manual-only retirement notice, remove external requests.
Verification: **CONFIGURATION_VERIFIED_NOT_EXECUTED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/423); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/9c6133d32d827b5992b02f62ebf6133977b8622e).
Files: `.github/workflows/hide-tipped-ai-props-tests.yml`, `.github/workflows/nba-consensus-test.yml`, `.github/workflows/nba-live-tracker-external-verification.yml`, `.github/workflows/nba-slate-resilience-tests.yml`, `.github/workflows/nba-ui-integrity.yml`, `.github/workflows/opponent_simulation_tests.yml`, `.github/workflows/verify-live-tracker-espn.yml`, `iphone_bot/fetch_game_moneylines.py`, `iphone_bot/fetch_odds_scores.py`, `iphone_bot/fetch_props.py`, `iphone_bot/tests/test_fetch_props.py`, `iphone_bot/tests/test_paid_odds_disabled.py`, `iphone_bot/tests/test_root_redirect.cjs`
Runs: 

### D10 — high — PR #424
Tracking coverage publication failed after three successive main push conflicts.
Root cause: Only three immediate retries and re-use of a saved stale report instead of newest source inputs.
Change: Recompute after each fresh fetch/reset; ten bounded attempts with backoff; explicit failure on exhaustion; PR cannot publish.
Verification: **PUBLIC_JSON_AND_HOSTED_EXECUTION_VERIFIED**. [PR](https://github.com/damiensandoval77-lang/Sports-Bot/pull/424); [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/93321d4ea27d52a16ecf066c3796bbdbcedabb9b).
Files: `.github/workflows/nba-tracking-coverage.yml`, `iphone_bot/tests/test_tracking_coverage_workflow.py`
Runs: [43475664143](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43475664143), [43475664430](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43475664430)
Production proof: [run](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43476029907); [public output](https://damiensandoval77-lang.github.io/Sports-Bot/tracking_coverage_status.json), generated 2026-11-13T17:46:14.789647+00:00, read 2026-11-13T17:47:27.165015+00:00.

## Branches, workflows, tests and security

Fetched 425 active heads and 424 discoverable PR tips. Earlier ancestry comparisons remain pinned in branches-final.json.gz; latest ref inventory is branches-closeout.json.gz. Deleted unreachable tips and execution of every historic revision are not covered. Seven pre-existing open PRs were reviewed; conflicts remain in #307, #249, #135 and #3. Old UI and research proposals were not blindly merged. A separate actor merged #422; it is not credited as this cycle's repair.

All 174 workflow definitions and histories were queried. 173 have run evidence; manual nba-backtest-real-market.yml returned none. All 83 scheduled definitions have observed runs. [Every workflow and sampled result](workflows.md). The 2,124 sampled run observations contain 1,413 successes, 247 failures, 456 cancellations, four skips and four in-progress statuses at sampling time; these are historical counts, not current defect counts.

Final static audit: 1,225 tracked files, 571 Python AST checks, 246 JSON parses, 38 JavaScript syntax checks, 174 workflows: zero errors and 45 architecture warnings. 390 mutable action references remain as supply-chain hardening findings. Targeted workflow scan found no pull_request_target, direct untrusted event text in shell, or whole secrets-context dump matches; that is not exhaustive taint analysis or a git-history secret scan. 242 distinct targeted local checks passed, plus hosted CI and production runs documented in receipt.json.

## Data, grading and actual deployment

NBA season calendar: 1,200 fixtures; NFL: 272. ESPN independently matched all nine NBA game identities and tip times using existing canonical aliases. All nine current NBA games have saved standard quotes and forecasts, but 16 of 371 current offers lack eligible primary forecasts (355 matched). There are 607 archived standard quotes, 28 archived thresholds missing primary forecasts (12 have separate research receipts; 16 no AI receipt), 904 AI-only records, and 582 future line-backed forecasts. No research estimate is promoted to primary solely to make readiness green.

November 12 saved NBA accounting: 388 AI records = 332 graded + 56 verified DNP exclusions; zero unaccounted captured records. Separate research ledger: 327 = 318 settled + nine void; zero overdue. This does not prove an uncaptured market existed or can be reconstructed. NFL: 135 standard grades including three pushes; 52 wins / 80 losses = 39.39%; zero standard pending. 932 historical alternate-tier grades and four alternate pending rows remain excluded. Fresh ESPN NFL collection at 17:23:58 matched WAS 24 NYG 21 and all 18 public player records exactly.

Official-source recovery: hosted run43468528082 independently verified 90/90 finals, zero failures, 2,107 player rows. The bounded 90-game research window leaves two insufficient-history contexts. One additional genuine CHI final was recovered separately: 91 games / 2,134 rows / 89 DNP rows, covering all 14 upcoming research contexts. This extended cache is retained alongside the receipt, not promoted into historical pretip forecasts or production probabilities.

Phone-width deployed check: 390x844 Chromium emulation, nine checks passed, 382 cards, no JavaScript errors, release/assets match. [Hosted phone evidence](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43462996631/artifacts/14057518209). Interactive public checks verified Over/Under, projections, Dame's Take placement, NBA saved-line/game detail, and NFL final/player detail. At 17:47 the public release and asset manifest still match that phone-tested release. Physical iPhone/Safari and actual 30-second active-game updates were not observed; no games were live during checks. Independent public HTML/JSON probe at 17:27 passed with 360 comparison rows; comparison count is distinct from primary-model eligible coverage.

## Remaining blockers and limits

- **B1 — Remaining, high:** Six players have only 3-7 qualifying same-team opportunity-history games; primary requires 8. Preserve explicit unavailable state; cannot invent history or promote unvalidated research estimates.
- **B2 — Recovered during run, high:** Transient PrizePicks freshness warning recovered by existing scheduled publication at 17:19:22 UTC. No paid refresh was initiated by this audit; source readiness READY on final readback.
- **B3 — Remaining, high:** Legacy branch Pages deployment cancellations and races. Repository owner must select Settings > Pages > Build and deployment > Source > GitHub Actions; connector cannot change setting and browser lacks authenticated admin session.
- **B4 — Remaining, medium:** No complete 72-hour clean production window or active-game verification during this run. Do not force release gate green; requires actual future observations.
- **B5 — Remaining, medium:** Remaining mutable action references are supply-chain hardening findings, not proof of an exploited vulnerability. Critical touched publisher actions pinned; broad unrelated workflow changes could activate prohibited provider work..
- **B6 — Remaining, medium:** Manual Underdog X diagnostic lacks UNDERDOG_X_BEARER_TOKEN. No secret changes or paid X access attempted. Full Underdog end-to-end coverage remains unverified..

Missing authentic pretip evidence is not recoverable by running a model after tip. Historical absence was not converted into grades. Full Underdog pretip-to-grade coverage remains unverified. No paid provider request, Replit request, secret change, fabricated market, fabricated forecast or fabricated grade was made by this audit.

GitHub Pages administration is the concrete user-side action: select Settings > Pages > Build and deployment > Source > GitHub Actions. The connected API has no settings mutation and the browser is signed out, so the existing controlled publisher cannot replace branch-based native Pages deployment from this session. Native cancellations remain unresolved.

Please notify Damien through enabled ChatGPT mobile notifications. Delivery has not been confirmed.

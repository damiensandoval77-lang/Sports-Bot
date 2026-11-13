# Sports-Bot active repair cycle — PARTIAL

Run start: 2026-11-13T22:28:34+00:00; evidence cutoff: 2026-11-13T22:59:14.399783+00:00. Seven code/test defects repaired in five merged PRs. Three browser behaviors independently verified live; four backend/security defects verified by regression/CI, with production jobs/output checked where applicable. Three operational findings and two verification limitations remain.

Initial main: `bc35651e88e935c856abfb26186adea2ca4b0085`. Latest observed main: `7303ae5848d54b312e8745c80fa1dbf224439b45`. Live release: `dp-under-detail-20261113-r38`.

## Repair log

### D1 — high — Stalled feed can hang application startup
[PR #427](https://github.com/damiensandoval77-lang/Sports-Bot/pull/427) · [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/0ad4eb949b494207395d7b1cb31dc480900d4d5c)

Root cause: Feed requests and body parsing lacked a bounded deadline.
Before: An unresolved fetch/body promise could keep board startup waiting.
After: Shared fetchData aborts/rejects after 8 seconds and existing fallback paths can continue.
Tests: 4 helper cases; 78 targeted Node tests; CI pipeline 43520562660 passed.
Production evidence: Public deployed actual helper rejected synthetic stalled same-origin request in 120.4ms Chromium / 122ms WebKit with test timeout 120ms.
Outcome: **VERIFIED_LIVE**

Files: `.github/workflows/dames-picks-version-e.yml`, `docs/dames-picks/dames_take.js`, `docs/dames-picks/feeds.js`, `docs/dames-picks/index.html`, `docs/dames-picks/live_direct.js`, `docs/dames-picks/provisional.js`, `docs/dames-picks/release.json`, `docs/dames-picks/short_history.js`, `requirements.txt`, `scripts/e2e_live_site.py`, `tests/test_feed_deadlines.cjs`
Runs: [43520562660](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520562660), [43520829975](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520829975), [43522674315](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674315)

### D2 — high — Vulnerable Tornado dependency
[PR #427](https://github.com/damiensandoval77-lang/Sports-Bot/pull/427) · [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/0ad4eb949b494207395d7b1cb31dc480900d4d5c)

Root cause: requirements.txt pinned Tornado 6.6; pip-audit reported CVE-2026-126347.
Before: PR pipeline 43519837338 failed security audit.
After: Pin upgraded to 6.6.1; security gate retained and subsequent pipeline passed.
Tests: pip-audit and full PR pipeline 43520562660.
Production evidence: Merged source dependency fixed; no browser exploit simulation was performed.
Outcome: **SECURITY_CI_VERIFIED**

Files: `.github/workflows/dames-picks-version-e.yml`, `docs/dames-picks/dames_take.js`, `docs/dames-picks/feeds.js`, `docs/dames-picks/index.html`, `docs/dames-picks/live_direct.js`, `docs/dames-picks/provisional.js`, `docs/dames-picks/release.json`, `docs/dames-picks/short_history.js`, `requirements.txt`, `scripts/e2e_live_site.py`, `tests/test_feed_deadlines.cjs`
Runs: [43519837338](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519837338), [43520562660](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520562660)

### D3 — medium — Conflicting duplicate minutes could be re-admitted
[PR #3](https://github.com/damiensandoval77-lang/Sports-Bot/pull/3) · [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/57f75152cfef7c7755a299b9cebe2db56e0b58cd)

Root cause: A later repeated value restored a player-day previously rejected for conflicting minutes.
Before: 30,42,30 sequence could restore the conflicting sample.
After: Conflicted player-day remains excluded.
Tests: Original PR regressions reproduced failures; 33 targeted tests passed after repair.
Production evidence: Postmerge minutes/injury pipeline 43521131098 succeeded; public minutes validation refreshed 22:40:29Z, research-only adjustments preserved.
Outcome: **REGRESSION_AND_PRODUCTION_EXECUTION_VERIFIED**

Files: `.github/workflows/nba-schedule.yml`, `.github/workflows/research-safety-ci.yml`, `iphone_bot/fetch_official_injuries.py`, `iphone_bot/minutes_model_v2.py`, `iphone_bot/tests/test_minutes_model_v2.py`, `iphone_bot/tests/test_research_upgrades.py`
Runs: [43521130920](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521130920), [43521131098](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521131098)

### D4 — high — Undated injury fragments accepted
[PR #3](https://github.com/damiensandoval77-lang/Sports-Bot/pull/3) · [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/57f75152cfef7c7755a299b9cebe2db56e0b58cd)

Root cause: Parser accepted a status fragment without game-date context.
Before: Undated fragment produced Out with game_date null.
After: Missing game-date context rejected; current provider provenance rules retained.
Tests: Regression reproduced before patch; included in 33 passing targeted tests.
Production evidence: Public injury_context refreshed 22:40:30Z: 69 players, zero undated records. Malformed edge case verified by regression, not observed naturally in production.
Outcome: **REGRESSION_AND_PRODUCTION_EXECUTION_VERIFIED**

Files: `.github/workflows/nba-schedule.yml`, `.github/workflows/research-safety-ci.yml`, `iphone_bot/fetch_official_injuries.py`, `iphone_bot/minutes_model_v2.py`, `iphone_bot/tests/test_minutes_model_v2.py`, `iphone_bot/tests/test_research_upgrades.py`
Runs: [43521131098](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521131098)

### D5 — high — First/new-slate boxscore validation bypass
[PR #249](https://github.com/damiensandoval77-lang/Sports-Bot/pull/249) · [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/3800a1bfb7b8816bfed90b52d1825112af4320aa)

Root cause: Early-return publication paths bypassed per-game structure and identity validation.
Before: First/new-slate malformed games, duplicates or invalid player_rows could publish.
After: Parse validates each game before any early return; existing partial merge and final-state safeguards retained.
Tests: Five failing regression cases before fix; 14 targeted tests passed afterward; CI 43521072656 passed.
Production evidence: Postmerge collector 43521470787 passed; public independent tracking refreshed 22:46:10Z. NBA pregame means no natural malformed live event observed.
Outcome: **REGRESSION_AND_PRODUCTION_EXECUTION_VERIFIED**

Files: `iphone_bot/merge_nba_player_boxscore_publish.py`, `iphone_bot/tests/test_merge_nba_player_boxscore_publish.py`
Runs: [43521072656](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521072656), [43521470787](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521470787)

### D6 — medium — Deployed phone verification omitted WebKit and detail flows
[PR #307](https://github.com/damiensandoval77-lang/Sports-Bot/pull/307) · [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/4888a4ef6ce416791438644f32e4a40ddd4c582a)

Root cause: Browser coverage did not exercise both engines and actual NBA/NFL details.
Before: Top-level checks could miss phone detail regressions.
After: Chromium/WebKit 390px touch matrix checks exact deployed assets, player/game details, Dame’s Take placement, overflow and JS errors; bounded screenshots.
Tests: 3 mobile-health tests and Python compile; CI passed.
Production evidence: Both engines PASS in 43521955806 and final 43522674315; 409 board cards, 9 NBA games, 15 NFL games; NBA/NFL player and game detail checks pass.
Outcome: **VERIFIED_LIVE**

Files: `.github/workflows/live-site-e2e.yml`, `scripts/e2e_live_site.py`
Runs: [43521955806](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521955806), [43522674315](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674315)

### D7 — low — Under detail box remained white
[PR #428](https://github.com/damiensandoval77-lang/Sports-Bot/pull/428) · [merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/0a60fbbfbff0cff8d455b9bc1d2592bfdeac1dee)

Root cause: .lean.under CSS background was white.
Before: Under player detail did not use requested red treatment.
After: Background #ff6b7a; coherent r38 assets and release manifest.
Tests: 78 targeted Node tests; PR checks 12 success, one intentional deployed-main-only skip.
Production evidence: Actual public Under card computed rgb(255,107,122) in Chromium and WebKit; WebKit screenshot visually inspected.
Outcome: **VERIFIED_LIVE**

Files: `docs/dames-picks/dames_take.js`, `docs/dames-picks/feeds.js`, `docs/dames-picks/index.html`, `docs/dames-picks/live_direct.js`, `docs/dames-picks/provisional.js`, `docs/dames-picks/release.json`, `docs/dames-picks/short_history.js`, `scripts/e2e_live_site.py`
Runs: [43522674315](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674315), [43522674263](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674263)

## Remaining findings and exact blockers

### B1 — Primary-model coverage incomplete — BLOCKED_EVIDENCE
Current 348/365 offers matched; 17 missing across seven players with fewer than eight recorded current-team games. Archive: 682 standard quotes, 36 without frozen primary threshold: 15 separate research, 21 without AI receipt.
Same-run workaround: Existing trained short-history/research paths kept separate; recovery and fresh quote feed examined. Did not lower eligibility or fabricate predictions/pretip timestamps.
Required resolution: Authentic eligible pretip history plus validated model support, or independently validated short-history production model. Past uncaptured evidence cannot be recreated truthfully.

### B2 — Legacy sportsbook-dependent AI/comparison jobs have stale inputs — BLOCKED_USER_COST_CONSTRAINT
43519076571 and 43514736498 fail freshness guards.
Same-run workaround: Retained prior board and guards; standard PrizePicks refresh occurred through existing automation at 22:44:09Z, with current line freshness healthy.
Required resolution: No-cost valid source replacement or deliberate retirement after consumer/dependency review. No paid polling authorized.

### B3 — Native Pages cancellations and duplicate publication control — BLOCKED_ADMIN_ACCESS
Public convergence reports source_mode legacy_branch. Connector does not expose Pages settings/admin writes; browser settings route signed-out 404.
Same-run workaround: Verified eventual native deployment and all r38 asset hashes using existing convergence workflow; no false deploy-pages claim.
Required resolution: Repository owner: Settings > Pages > Build and deployment > Source = GitHub Actions. Existing controlled workflow must then be verified in Actions mode.

### V1 — Per-workflow history not completely retrievable — BLOCKED_HISTORY_ACCESS
178 registered workflow histories attempted: 57 retrieved, 121 returned HTTP403. Connector rejects workflow-specific collection endpoint.
Same-run workaround: Fetched global recent run samples, individual failed jobs/logs and all 175 current workflow definitions.
Required resolution: Supported authenticated Actions workflow-history read capability; exact exceptions persisted in workflow-history.json.gz.

### V2 — Active NBA pacing and all-provider historical completeness not independently proven — NOT_OBSERVED
No active NBA game before 00:00UTC; full Underdog quote ingestion and every historical branch semantic execution not completed.
Same-run workaround: Fresh NBA/NFL ESPN reconciliation, public phone flows and current archive grading inspected.
Required resolution: Live-game observations with real totals, authentic provider coverage evidence; do not count missing observations as pass.

## Workflow failures and recovery

- [43519837338](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519837338) — pipeline: Tornado 6.6 security vulnerability; fixed by 6.6.1 in PR427; 43520562660 passed.

- [43519076571](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519076571) — NBA trained AI: Legacy sportsbook quote source older than six hours. Paid refresh forbidden; stale-data gate retained.

- [43514736498](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43514736498) — AI comparisons: NO_FRESH_PAIRED_PROPS; old board preserved. No paid refresh dispatched.

- [43519584064](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519584064) — Heartbeat: capture_integrity failed; recovery dispatched existing NBA/readiness workflows but missing primary coverage persists.

- [43508627882](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43508627882) — Full repository audit: Static and branch jobs passed; production recovery still lacked 31 frozen primary markets at that run, report job correctly failed.

- [43513614075](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43513614075) — Unified release gate: NBA capture and production / unified artifacts degraded; NFL ready; healthy streak zero.

- [43519246203](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519246203) — Unified integrity: Report successfully committed 83e2b414; process exited 2 for degraded coverage, not failed write.

- [43520828939](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520828939) — Native Pages: Cancelled during repeated native branch publishes; later deployment converged.

- [43520859533](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520859533) — Native Pages: Cancelled; branch-mode publish race remains administratively blocked.

- [43520928878](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520928878) — Native Pages: Cancelled; eventual 43521005832 succeeded.

- [43520964647](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520964647) — Native Pages: Cancelled; public r38 subsequently verified.

- [43520971741](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520971741) — Native Pages: Cancelled; public r38 subsequently verified.

## Coverage and grading

{
  "nba_schedule_today": 9,
  "nba_fixed_season_games": 1200,
  "nfl_season_games": 272,
  "nba_current_standard_offers": 365,
  "nba_current_primary_matched": 348,
  "nba_current_primary_missing": 17,
  "nba_archived_standard_quotes": 682,
  "nba_archived_primary_missing": 36,
  "nba_missing_with_research": 15,
  "nba_missing_without_ai_receipt": 21,
  "nba_line_backed_forecasts": 649,
  "nba_ai_only_forecasts": 904,
  "readiness_checks_passed": 9,
  "readiness_checks_total": 10,
  "quote_source_generated_at": "2026-11-13T22:44:09.606794Z",
  "current_quote_stale_count": 0,
  "current_quote_staleness_scope": "Readiness quote component; not all repository artifacts",
  "nba_first_tip": "2026-11-14T00:00:00Z",
  "nfl_espn_player_rows_reconciled": 18,
  "nfl_espn_mismatches": 0
}

{
  "nba_nov12_ai_recorded": 388,
  "nba_ai_graded": 332,
  "nba_verified_dnp": 56,
  "nba_ai_unaccounted": 0,
  "nba_captured_prizepicks": 327,
  "nba_settled": 318,
  "nba_void": 9,
  "nba_overdue_captured": 0,
  "nfl_standard_graded_including_pushes": 135,
  "nfl_standard_pushes": 3,
  "nfl_standard_decisions": 132,
  "nfl_standard_wins": 52,
  "nfl_standard_losses": 80,
  "nfl_standard_hit_rate_percent": 39.39,
  "nfl_standard_pending": 0,
  "nfl_alt_grades_excluded": 932,
  "nfl_alt_pending_excluded": 4,
  "nfl_void": 16,
  "missing_uncaptured_historical_count": null,
  "missing_uncaptured_historical_status": "Unknown; cannot reconstruct without authentic pretip evidence."
}

All seven original open PRs were addressed. #3/#249/#307 were repaired, tested and merged. #135 targeted the retired root renderer; #132/#72/#272 were obsolete temporary diagnostics superseded by maintained verification. Their bodies record the disposition; branches were preserved. New #427/#428 merged. Zero open PRs at final query.

Branch inventory: 429 heads and 428 historical PR tips fetched and ahead/behind compared; unavailable deleted refs and complete semantic execution of every past revision are not covered. See branches.json.gz.

All 175 definitions statically checked; 0 static errors, 45 PRODUCTION_UNIT_TEST_GATE warnings. These are architectural warnings, not 45 proven outages. 381 action uses remain mutable references; this is unresolved hardening scope, not a claim of 381 known compromised actions. Full dependency/model security certification was not achieved. See workflows.md for every definition and workflow-history.json.gz for the exact 121 access exceptions.

Public r38 verification: 16 checks per engine PASS at 22:52:59Z; Chromium and WebKit at 390px. Exact six asset hashes, stalled-feed deadline, red Under detail, NBA/NFL player details, Dame’s Take immediately after projection, game boxscore sections, no overflow and no JS exceptions verified. Screenshots and JSON included. This is emulation against the deployed public app, not a physical iPhone test. No active NBA game existed yet, so live 30-second pacing during play was not observed.

NBA today: all nine ESPN game identities/tip times reconciled; full fixed schedule 1200 games. NFL season 272 games; current ESPN published player rows reconciled 18/18. Standard grading excludes alternative tiers. No post-tip forecast, line or grade was fabricated. Full Underdog quote ingestion remains unverified; missing X injury-monitor token is not evidence that the quote feed works or fails. Free official injury context refreshed successfully.

Existing two-hour automation remains enabled and unchanged. Prior run returned a full report; current run also returns one. No no_update. Notification delivery cannot be confirmed by the available tools.

**Please notify Damien through enabled ChatGPT mobile notifications. Delivery has not been confirmed.**

Machine-readable source: receipt.json. All data timestamps are explicit snapshots and background data workflows continue running.

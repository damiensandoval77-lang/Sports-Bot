# Sports-Bot audit and repair log

Status: PARTIAL. Started 2026-11-14T04:34:03+00:00; checks completed 2026-11-14T05:00:08.755901+00:00. Five repair categories completed; three verified in public production, one across five branch heads, one in CI.

## Findings and repairs

### R1 — Browser recovery dispatched the wrong workflow

- **severity**: high
- **root_cause**: public_browser recovery invoked data publisher, which does not refresh the browser receipt
- **repair**: Target verify_unified_dames_browser.yml, retain dedup/backoff and shorten successful browser recheck cooldown
- **pr**: 442
- **merge**: feed3202382e3df5bd19a1fc4820498f905f0c94
- **status**: VERIFIED_LIVE
- **before**: Stale failed browser receipt held readiness degraded after data recovery
- **after**: 7/7 required production checks READY and public receipt refreshed
- **tests**: 74 targeted tests; PR CI; production run 43557621462
- **files**: ["iphone_bot/readiness_recovery.py", ".github/workflows/production_readiness.yml"]
- **pr_url**: https://github.com/damiensandoval77-lang/Sports-Bot/pull/442
- **merge_url**: https://github.com/damiensandoval77-lang/Sports-Bot/commit/feed3202382e3df5bd19a1fc4820498f905f0c94

### R2 — Settlement publication did not follow completed grading

- **severity**: high
- **root_cause**: Settlement workflow lacked completion triggers for both authoritative graders
- **repair**: Same-repository main workflow_run triggers with serial concurrency
- **pr**: 443
- **merge**: a34b4ea67f37549f478fae208ecc9762a338e0cd
- **status**: VERIFIED_LIVE
- **before**: Public receipt 1442 graded /347 pending while ledger 1511/278
- **after**: Automatic completion run 43557958913 refreshed receipt; subsequent DNP completion run 43558720383 passed; public totals reconcile
- **tests**: 15 settlement tests, PR CI and actual workflow_run execution
- **files**: [".github/workflows/nba-published-pick-settlement.yml", "iphone_bot/tests/test_published_pick_settlement.py"]
- **pr_url**: https://github.com/damiensandoval77-lang/Sports-Bot/pull/443
- **merge_url**: https://github.com/damiensandoval77-lang/Sports-Bot/commit/a34b4ea67f37549f478fae208ecc9762a338e0cd

### R3 — Five archived branch heads contained invalid workflow YAML

- **severity**: medium
- **root_cause**: Colon in unquoted step name
- **repair**: Quote the step name in each current branch, forward-only CAS updates
- **status**: VERIFIED_BRANCH_ONLY
- **before**: One invalid source blob on five branch heads
- **after**: 445 branch heads, 2001 unique source blobs, zero syntax errors
- **commits**: ["f5512959c331675d514e0ff09277dfd6785b96a5", "05cc421ec8d19801ba28322fc7db59ab5f374abf", "8a851d3fbbe8703415bd9120a8111d516b211928", "c0e334e92beabe3ae37bbaee00cb64c2bf1e70de", "d245ac9e508b266a3b0d9335b98e3d1caf357c7d"]
- **files**: [".github/workflows/research-pregame-evidence.yml"]
- **tests**: Python AST, node --check, bash -n, YAML parsing across fetched branch heads

### R4 — Official verified DNP results were left pending

- **severity**: high
- **root_cause**: Primary and research DNP readers disagreed with authoritative NBA_CDN_FINAL/ESPN_FINAL provenance
- **repair**: Accept exact-identity explicitly verified official DNP results; reuse authoritative observed_final predicate for separate research/baseline exclusions; reject undocumented exclusions
- **pr**: 444
- **merge**: 13326a54dbdcea7ffa09ffce97ff5893185b7db2
- **status**: VERIFIED_LIVE
- **before**: 16 primary picks pending; 21 research picks unsettled despite verified DNP evidence
- **after**: Primary 1511 graded,51 DNP,262 pending; research47 void,263 unsettled. Zero immutable pretip field changes
- **tests**: Regression failures reproduced before;89 related tests passed;11 PR checks passed; production graders43558695023/43558694974 passed; public HTTP200 grading data verified04:58 UTC
- **files**: ["iphone_bot/multimarket_forecast_ledger.py", "iphone_bot/published_pick_settlement.py", "iphone_bot/grade_standard_quote_ai_research.py", "iphone_bot/grade_frozen_baseline_join.py"]
- **pr_url**: https://github.com/damiensandoval77-lang/Sports-Bot/pull/444
- **merge_url**: https://github.com/damiensandoval77-lang/Sports-Bot/commit/13326a54dbdcea7ffa09ffce97ff5893185b7db2

### R5 — Pull-request CI depended on live provider quote availability

- **severity**: medium
- **root_cause**: Multi-market PR workflow ran production capture and current-board generation after tip
- **repair**: Keep all fixture/regression checks on PRs; gate four live generation/validation steps to non-PR events. Production fail-closed gates unchanged
- **pr**: 444
- **merge**: 13326a54dbdcea7ffa09ffce97ff5893185b7db2
- **status**: VERIFIED_CI_ONLY
- **before**: CI43558356194 failed Verified standard live lines unavailable after tests passed
- **after**: Updated PR444 head86f4d6d6883fa4b576d6a5e4773fc785ee572da2 passed all11 checks
- **files**: [".github/workflows/nba-new-ai-all-markets.yml", "iphone_bot/tests/test_multimarket_workflow_dependencies.py"]
- **pr_url**: https://github.com/damiensandoval77-lang/Sports-Bot/pull/444
- **merge_url**: https://github.com/damiensandoval77-lang/Sports-Bot/commit/13326a54dbdcea7ffa09ffce97ff5893185b7db2

### B1 — Historical primary-model capture evidence incomplete

- **severity**: high
- **status**: BLOCKED_MISSING_IMMUTABLE_EVIDENCE
- **count**: 60
- **details**: 9 changed thresholds from original frozen line and51 markets never primary-frozen;7 have separate research receipt,53 have no AI receipt. Existing forecasts and exact thresholds cannot be fabricated posttip. Heartbeat and release gate correctly remain red.
- **workaround_attempt**: Examined archived captures, research cohort and branch/PR history; kept separate cohorts; fixed recoverable DNP grading without inventing evidence

### B2 — Repeated legacy Pages deployment cancellation

- **severity**: high
- **status**: RECOVERED_OUTPUT_ADMIN_FIX_BLOCKED
- **details**: Latest successful Pages runs43558860916,43558902420,43559021208,43559106496 delivered corrected grading JSON; recurring cancellation root remains.
- **blocker**: GitHub connector excludes Pages administration; browser settings page is signed-out404
- **required_action**: Repository owner: Settings > Pages > Build and deployment > Source: GitHub Actions; then verify existing controlled Pages workflow. No secret changes required.

### B3 — Browser-direct ESPN receipt unavailable

- **severity**: medium
- **status**: UNVERIFIED_DIRECT_SOURCE
- **details**: Current real browser probe attempted direct source but received false;3 active NBA games had no missing score/player coverage through published/raw fallbacks.30-second timer exists, but end-to-end direct update freshness is not certified.
- **workaround_attempt**: Verified free published/raw fallback, stale-data safeguards and phone rendering; no paid polling

### B4 — Fresh verified standard provider board unavailable

- **severity**: high
- **status**: BLOCKED_SOURCE_AVAILABILITY
- **details**: Current offers0 with stale/unverified source status, not certified empty coverage. Production generators correctly refuse output. All9 current slate games already started; no paid source refresh authorized.
- **workaround_attempt**: Used immutable pretip records for settlement and official free final results; did not fabricate future or posttip quote captures

## Evidence and exact coverage

[Machine-readable receipt](receipt.json), [all176 workflow definitions and initial recent runs](workflows.md), [121 workflow-history exceptions](workflow-exceptions.json), [later workflow runs](final-run-evidence.json), [public grading proof](live-grading-verification.json), [DNP before/after and immutable comparison](dnp-production-evidence.json), [branch syntax audit](branch-source-syntax.json), [180 Python test log](final-targeted-tests.log), [65 frontend tests](frontend-tests.log).

All summaries are bounded by recorded timestamps. In-progress games retain pending outcomes. Historical absent predictions cannot be recovered by running a new model after tip. No paid refresh, fabricated grade or secret change was made. Notify the user through enabled ChatGPT task notifications; delivery is not confirmed.

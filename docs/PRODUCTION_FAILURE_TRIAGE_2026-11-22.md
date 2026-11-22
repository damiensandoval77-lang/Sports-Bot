# November 22, 2026 — NBA/NFL production failure triage

This is a read-only evidence assessment. No model weights, odds API credits, frozen lines, grades, or published user-facing picks were changed.

## Verified GitHub Actions failures

| Workflow | Run | Observed evidence | Classification |
|---|---|---|---|
| Guarded live NBA points challenger | 45080871025 | `ValueError: No currently verified PrizePicks line source` in forecast-generation step | BLOCKED: line source |
| NBA production readiness and stability gate | 45080600498 | `status: DEGRADED`, 7/11 passing; `prizepicks_lines`, `pregame_capture`, `current_primary_model_coverage`, `nightly_grades` degraded | NOT READY |
| Unified Dame's Picks NBA + NFL integrity | 45080600496 | `Unified Dame's Picks integrity DEGRADED`; push rejected during report publication | NOT READY + concurrent writer collision |
| Grade immutable standard-line AI research receipts | Latest November 22 run | Workflow passed; no proof every eligible pregame line was graded | PARTIAL EVIDENCE ONLY |
| Native Pages build | Latest November 22 run | Build passed; does not prove line coverage, model quality or grade completeness | DEPLOYMENT ONLY |

## Independent repair tracks

### 1. Line availability and provenance (highest priority)
- Record source status as `available`, `not_offered`, `rate_limited`, `blocked`, `stale` or `unknown`, never silently convert errors into zero offered markets.
- Do not call the paid Odds API merely to validate PrizePicks coverage.
- Require timestamp, game/player/market identity, and standard-line type before a line can join an AI receipt.
- Only after a verified line source exists should the points challenger run against it; do not generate a pretend comparison.

### 2. Pregame immutable receipt completeness
- Reconcile every scheduled game to pretip frozen lines and AI forecasts.
- Show explicit unavailable reasons for any missing receipt. Do not backfill a pregame forecast using post-tip knowledge.
- Prevent the public UI from claiming a prediction existed before tip if it did not.

### 3. Nightly grading
- Count eligible frozen receipts, officially final games, grades, DNP exclusions, unresolved and overdue items.
- Require `eligible = graded + DNP + unresolved` with a reproducible immutable ledger.
- Never infer full gradeability from a successful workflow exit code.

### 4. Independent Git push writers
- Identify the exact output files written by the unified integrity workflow and overlapping scheduled jobs.
- Serialize writes per output path or use artifact-based reporting; retain newest-observation semantics.
- A push rejection must remain visible and cannot be interpreted as a successfully published report.

### 5. Production acceptance
- Verify source receipts, official boxes, model coverage, grade reconciliation and actual deployed phone-visible UI against the same release SHA.
- Require an observed complete NBA game and NFL game before clearing their respective live-readiness gates.
- A Pages build, green source test, or rendered cards alone is insufficient.

## Owner-independent work
- Source inspection, workflow dependency inventory, no-credit unit tests, guardrail changes, audit documents and CI verification.
- Do not activate a paid provider, rotate credentials, regrade history, alter frozen picks, or claim live fixes without real deployed evidence.

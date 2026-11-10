# Sports-Bot: Five-Phase Reliability-to-App Roadmap

**Established:** 2026-11-09  
**North star:** Two trustworthy sports analysis engines (NBA + NFL), sharing reliable infrastructure and ultimately presented in an iPhone-native app that can be shared with friends.  
**Current focus:** Phase 1 (NBA); Phase 2 (NFL) runs in parallel where safe.  
**Status legend:** `[x]` shipped code / verified evidence explicitly linked; `[ ]` unfinished or not yet verified. A merged PR or green unit test is **not** proof of live uptime.

## Non-negotiable principles

1. **Never fabricate data.** Preserve actual provider line, model projection, simulated probability, grading, provenance and timestamps as separate fields. Missing values remain unavailable; research-only probabilities are never called calibrated or verified betting edges.
2. **No silent failure.** Every refresh publishes status or produces a visible failed run/alert; the interface distinguishes fresh, degraded, stale, unavailable and pending.
3. **No destructive publishing.** Invalid/partial/unrelated new data must not erase previously verified snapshots; old snapshots must be clearly marked stale and are never silently relabeled current.
4. **Immutable pregame record.** Lock source, line, market, player/team/game ID, predicted outcome, model version and observation time before tipoff. Grade only against source-verified final statistics, with DNP/push/void/pending separate from wins/losses.
5. **Stable game/player identity.** Check official schedule vs browser navigation, lines, tracking and results by exact IDs and date. Avoid hard-coded nightly slates.
6. **Guard provider costs.** Reuse saved authentic data, bound paid calls/credits and allow top-up usage only where configured; do not assume remaining balance from a single header.
7. **One quality gate per phase.** Require evidence across real game nights rather than claiming "foolproof" or assigning arbitrary completion percentages.

## Phase 1 — NBA production reliability

**Goal:** Reliable nightly coverage from independent schedule and source collection through pregame prediction freeze, in-game tracking, verified finals and completed grading.

### 1A. Schedule and provider collection
- [x] Initial schedule reconciliation and eight-game November 9 browser check implemented (historical evidence; verify on each future slate).
- [x] Authentic PrizePicks source/site publishing integrity gate merged (PR #140).
- [ ] Dynamic schedule completeness check for **each Eastern date** based on independent official fixtures, including rollover and rescheduled games.
- [ ] Provider-status matrix: source available, partial pagination, stale, unavailable, paid request budget; verify each scheduled matchup separately.
- [ ] Recovery from missing market lines without fabricating prices, probabilities or "no lines exist" assertions.

### 1B. Prediction and simulation
- [ ] Freeze all eligible actual pretip predictions with player/game ID, line, source time, model version, injury state, opponent, minutes, and simulation inputs.
- [ ] Verify the opponent-aware modeling/simulation path (position defense, pace, minutes, teammate absences, season form, 20,000 draws where applicable) is wired to the displayed output.
- [ ] Display projection + over/under only when prerequisites are satisfied; show explicit reason otherwise.
- [ ] Establish per-market coverage metrics, calibration and holdout accuracy without cherry-picking or mixing simulated chance with observed hit rate.

### 1C. Live tracking and grading
- [x] Fail-safe live player boxscore publisher retained on failed refresh; concurrent update retries merged (PR #141).
- [ ] Confirm game-to-player identity and observed PTS/REB/AST/PRA vs frozen line/projection in the **real deployed mobile browser** after tipoff.
- [ ] Verify ongoing automatic updates, observation age, live pace and final result reconciliation for every started game.
- [ ] Resolve historical November 8 backlog: 24 ungraded AI forecasts tied to six Miami–Sacramento players; do not assume DNP absent independent evidence.
- [ ] Complete scheduled hourly/nightly auto-grading (wins, losses, pushes, voids, verified DNP, pending) with retry, missing-final diagnostics and immutable original predictions.
- [ ] Ensure scheduled runs visibly fail or alert when grading stalls.

### 1D. Reliability, monitoring and release gate
- [x] Initial independent guardrail test suite and browser-check integration merged (PRs #138–139).
- [ ] Add atomic publication/recovery to **all** NBA workflows, not just a single PrizePicks publisher.
- [ ] Last-good snapshots with explicit freshness and no time travel across parallel runners.
- [ ] Dynamic browser canary rather than fixed Nov 9 eight-game EXPECTED constant.
- [ ] Automated alert after repeated failed refreshes / missing games / overdue grades; documented recovery procedure.
- [ ] Fault-injection tests: unavailable feed, partial provider data, missing player, delayed workflow, stale snapshot, concurrent commits, wrong game ID, browser JS crash.
- [ ] **Exit gate:** seven consecutive real NBA game dates with verified all-scheduled-game navigation; no silent blank screens; every eligible saved pregame record settled or explicitly pending/void with a documented source reason; live observations and freshness audited; no unexplained grading backlogs. Measure success from published audit logs, not test count alone.

## Phase 2 — NFL production reliability

**Goal:** Independent NFL schedule, depth charts and usage, saved prop lines, opponent-aware predictions, game tracking and fully reconciled official finals.

### 2A. Source integrity
- [ ] Verify entire official season and weekly schedule, kickoff/timezone, BYEs, moved and postponed games.
- [ ] Complete consistent team/player/depth-chart identity and injury status with date-of-observation and source precedence.
- [ ] Integrate verifiable current-season boxscores, targets, snaps, routes/usage, pace and defensive positional splits (e.g. NFLverse / licensed-accessible data); track data freshness and source rights.
- [ ] Real authenticated provider lines when available; never invent absent PrizePicks lines.

### 2B. NFL predictions and historical evaluation
- [ ] Quantify whether depth-chart, opponent defense, snap/route/target and injury features improve time-split validation against baseline.
- [ ] Keep model versions and season history isolated from NBA; freeze predictions before kickoff; record edge, projection and available line honestly.
- [ ] Validate common per-stat coverage, model error, projected lean and season over/under occurrence history.

### 2C. NFL tracking, grading, reliability
- [ ] Verify scheduled player boxscore collection + name matching, original pick snapshots, actuals and grades **for every completed game**.
- [ ] Ensure retry/recovery, final result reconciliation, missing-game alerts and full historical audits.
- [ ] Reuse shared read-only health reporting and last-good publication patterns without coupling NFL failures to NBA.
- [ ] **Exit gate:** seven consecutive applicable NFL game dates (including a full multi-game slate) with independent schedule reconciliation, no silently dropped predictions, tracked players and end-to-end source-verified grading; all exceptions visible.

## Phase 3 — Merge into one platform (without merging model logic)

**Goal:** A unified reliable platform with independently deployable NBA and NFL sports adapters.

- [ ] Inventory both repos/data flows and establish baseline before migration.
- [ ] Define common canonical records: `Sport`, `Game`, `Team`, `Player`, `Market`, `ProviderQuote`, `ModelPrediction`, `LiveObservation`, `FinalResult`, `Grade`, `HealthEvent`.
- [ ] Establish immutable IDs, UTC timestamps with Eastern display, original quote/model hashes and reproducible model versioning.
- [ ] Create shared ingestion/normalization, persistence, event queue, worker retries, health/alerts and API with NBA/NFL-specific adapters.
- [ ] Use transactional or versioned snapshot promotion, idempotency keys, concurrency controls and rollback.
- [ ] Run both old and new services in shadow mode; compare records and grading outputs across full game dates.
- [ ] Cut over one sport at a time; preserve working legacy UI and automatic rollback.
- [ ] **Exit gate:** multi-day parity between old and unified systems, no missing/fabricated lines/grades, sport failure isolation, tested rollback and production performance target.

## Phase 4 — iPhone app interface

**Goal:** A dependable mobile user experience atop the proven backend, not a browser wrapper that hides outages.

- [ ] Choose native iOS (SwiftUI) vs cross-platform after measuring maintenance and distribution needs.
- [ ] Build navigation: NBA/NFL switch, horizontal matchups, current game, verified props, model projection/lean, confidence labeling, season/L5/L10/minutes, opponent context.
- [ ] Started games move to live tracker view with live actual vs frozen projection/line, update age and pace; never overwrite the frozen pick.
- [ ] Historical grading dashboard with filters by sport/market/model, sample size, confidence calibration and clear pending reasons.
- [ ] Fast cache, retries, offline/stale badges, crash reporting, accessible tap targets and responsive iPhone layouts.
- [ ] Notifications for real model publication, game start, final grades and degraded feeds (opt-in; avoid unsolicited wagering prompts).
- [ ] Authentication, privacy controls, secure server-side provider keys, and controlled friend beta access.
- [ ] **Exit gate:** TestFlight beta with genuine multi-day live usage, error-free core flows at agreed rate, no divergence from backend records, and verified graceful degraded/offline states.

## Phase 5 — Production hardening and controlled release

**Goal:** Long-term sustainable operation and safe rollout to friends.

- [ ] Define SLOs: data freshness, scheduled coverage, publish lag, live tracking completeness, grading lag, and app crash-free sessions.
- [ ] Centralized structured logs, dashboards, paging/on-call ownership, runbooks, backup restore drills, budget alerts, security and access review.
- [ ] End-to-end synthetic checks, chaos/recovery drills, rollback verification and automated regression on every release.
- [ ] Capacity and cost analysis; provider terms/rate limits; fail-safe behavior during outages.
- [ ] User feedback, staged releases, update compatibility, account security and privacy policy where relevant.
- [ ] **Exit gate:** at least 30 days measured stable operation after beta, incident/recovery review and acceptance of remaining risks; then expand rollout cautiously.

## Current objective and evidence log

- Last inspected November 9 NBA production readiness: **DEGRADED** (3/6 required components passing); provider board partial and stale legacy published pick cards. Historical browser canary successfully rendered 204 cards for 8 scheduled matchups, but that alone does not prove live player tracking or grading.
- November 8 grading status: 1,676 captured PrizePicks records settled/voided; **24 separate frozen AI forecast markets remain ungraded** pending independently verified final player rows or inactivity.
- PR #138: independent integrity guardrails (merged).
- PR #139: run guardrail unit suite in browser-check workflow (merged).
- PR #140: authenticated PrizePicks source-to-site publishing gate (merged).
- PR #141: protect independent player tracking output and retry concurrent writes (merged).

## Progress reporting protocol

For each subtask record: **owner, PR/commit, unit-test result, actual production-run URL, last-good timestamp, coverage counts, exceptions, and next action**. Status can be `NOT_STARTED`, `IMPLEMENTED_UNVERIFIED`, `LIVE_VERIFIED`, `BLOCKED`, or `DONE_EXIT_GATE`. Never infer completion from roadmap checkbox alone. Use a single audit report for nightly sports-specific readiness and a weekly seven-day rolling validation report.

**Immediate next actions:** (1) post-tip player-tracker browser verification and stale-feed checks, (2) resolve the 24 outstanding November 8 forecasts with independently verified evidence, (3) dynamic slate-aware browser canary, (4) cross-workflow snapshot fallback and alerts, (5) begin NFL gap inventory in parallel.

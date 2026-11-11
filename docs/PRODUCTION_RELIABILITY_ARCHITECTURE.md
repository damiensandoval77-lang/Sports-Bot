# Dame's Picks — Independent Production Reliability Assessment
**Evidence window:** November 10–11, 2026 (Eastern gaming slate).  
**Scope:** NBA + NFL unified app; standard PrizePicks and prospective Underdog ingestion.  
**Release classification:** **NOT READY FOR EXTERNAL USERS** until the acceptance gates below pass.

This assessment is grounded in repository files, actually published health reports,
and executed Actions tests. It does not claim browser-level access from every
phone or that all historical grades are correct merely because code passed CI.

## Verified baseline

The read-only topology tool `python scripts/audit_workflow_topology.py`
ran in GitHub Actions at 2026-11-11 02:22 UTC:

| Signal | Observed |
|---|---:|
| Workflow YAML files | 157 |
| Workflows with cron scheduling | 72 |
| Cron schedule entries | 80 |
| Workflows with possible Git commits/pushes | 89 |
| Shared `nba-prop-feed` concurrency lane | 8 workflows |
| Watched publication targets with 2+ distinct potential writers | 5 |

The last number is a lower bound. Writer detection is text-based and can miss
writes in Python or dynamic shell expansions. Actual cancellations and stale
publishing must be confirmed from workflow run history, not guessed from the
repository configuration. The shared concurrency lane includes results,
settlement, AI, research, and feed updates.

Published November 10 snapshots showed 6 known NBA games and 253 saved
line-backed predictions, plus 139 standard provider markets lacking a frozen
primary model (73 moved prices and 66 not modeled). Those 139 are **not** graded
picks and must remain separately labeled. The frozen market ledger had 443
records across slates, including multiple historical pretip line versions;
a November 11 settlement audit counted 148 graded, 11 official DNP voids,
and 284 pending **at that audit time**. These are not current lifetime metrics.

The public deployed-code/ESPN integration passed at 02:01 UTC for two games:
97 of 97 eligible live player values attached and both scores displayed by
the direct-feed adapter. This proves the deployed JS can process live data from
a server-side runner, **not** that every phone's browser may call ESPN or
that live player totals are persisted and subsequently graded.

## End-to-end pick lifecycle and failure boundaries

| Stage | Authoritative artifact today | Failure mode | Invariant / next change |
|---|---|---|---|
| 1. Official schedule | `docs/nba_schedule.json`; NFL schedule export | Missing next scheduled game / static cache | A scheduled fixture is visible independently of offers/models; source IDs and ET game dates required |
| 2. Provider offer | `docs/prizepicks*.json` / raw archived quotes | Missing or moved line; paid credit exhaustion; partial board | Only real two-sided **standard** offers; source timestamp, price, player, stat, tier and event ID recorded |
| 3. Model snapshot | current form + frozen model outputs | Long training or stale model; no eligible projection | Explicit model version and deterministic input snapshot ID; no guessed fallback projection |
| 4. Pretip capture | `docs/lagged_matchup_all_market_ledger.json` / NFL frozen archives | Multiple writers; new line versions counted twice; late captures | Append-only immutable versions; provider time ≤ capture time < actual tip; one designated primary published pick per market |
| 5. Publication | Git commit → Pages → JS cards | Cron latency, contested writes, Pages delays, cached/stale data | One canonical NBA/NFL endpoint; browser never labels stale rows live; deployment version in health |
| 6. Live tracking | independent NBA player/score snapshots, browser-direct ESPN | A new partial game list deletes other games; source blocked; ESPN abbreviations mismatch | Per-game identity and observed_at merge; no player extrapolation or DNP→0; source age visible |
| 7. Final verification | NBA/ESPN authenticated final sources, NFL official final boxes | Provider missing/lag; partially absent final | Require final status, exact player/team/game identity, official ID and source observation |
| 8. Grade/void | AI final and four-market ledgers / NFL grading archive | Shared Actions concurrency drops run; same data written concurrently; regrade ignores versions | Immutable result per exact original standard line, source-linked, tie/push/DNP handled without guessing |
| 9. Historical accuracy | audits, grade metrics, archived ledger | Inflated win rate from multiple price versions, stale totals | One agreed primary pick per market in headline results; other versions research-only |

**Current primary-pick policy proposed (requires approval before changing
historical hit rates):** keep every original line/version and its independently
verified settlement, but choose the last verified pretip *published* standard
offer for one player/stat/game/platform, at a fixed documented lock cutoff
(e.g. 5 minutes before tip). Store the designation once and never repoint it
after the game. Do not backdate or invent prior publication events.

## Confirmed defects and changes in this reliability branch

- `iphone_bot/merge_nba_player_boxscore_publish.py` formerly treated a newer
  partial report as a replacement for the whole slate. It now retains the most
  recently observed verified row **for each game**, preserving that row's
  original `observed_at` and keeping incomplete upstream coverage marked
  partial. Rejects contradictory game IDs, malformed data, same-day late
  regressions and previous-slate contamination.
- The expanded game-details view previously compared `NY` with `NYK`
  literally, even though standard card attachments used canonical aliases.
  Both now use the same known league-specific mapping.
- The production readiness recovery runner can trigger an extra paid provider
  job beyond scheduled calls. Automatic PrizePicks dispatch now enforces
  a maximum of six **started** workflow runs per UTC day and refuses a paid
  dispatch when run-history retrieval fails. Free recovery is not capped by
  this cost rule.
- Read-only workflow topology census runs in the existing integration CI,
  so adding evidence does not add a new scheduled writer.

No historical frozen pick/grade records were modified in these changes.

## Why GitHub Actions is not the appropriate live system

- Scheduled Actions are best-effort; they cannot guarantee a 30-second cadence.
- A concurrency group may retain one running plus one pending job; later
  queued arrivals replace older pending work, which can displace settlements.
- Separate jobs with Git write permission modify the same JSON outputs.
  Git refetch/rebase/retry is **not** a transactional database, especially when
  work computes grades before observing the most recent committed ledger.
- GitHub Pages is a static deployment/cache mechanism, not guaranteed live
  publish/subscribe. Browser-direct ESPN can be blocked for some clients.
- A Git-based datastore lacks unique constraints, row locks, audited
  transactions, efficient keyed queries, atomic capture+publish+settle, and
  an independent replayable job queue.

## Target architecture — preserve models and UI, replace the live engine

- **One always-on worker** deployed outside Replit, using a managed service
  or small VPS with supervised restart and backup. Prefer Postgres with daily
  backups and tested restore. Use a short independent scheduler plus a
  transactional job queue and idempotent retries.
- **Collectors:** league schedules (at fixed daily cadence), real provider
  standard offers (bounded quota and pretip windows), live NBA/NFL scores and
  player totals (free public/authorized feeds), official final boxscores.
  Every response carries source, event ID, observed_at and validity.
- **Append-only DB:** `provider_observations` immutable hash/version,
  `model_snapshots` with input fingerprints, `pick_versions` with original
  offer/model/lock, `published_primary_picks` uniquely keyed by
  platform+game+player+stat, `game_observations` keyed by source/time,
  `verified_results` keyed by game+player+stat+official source,
  `settlement_events` keyed by exact pick version and immutable source ID,
  `job_runs`, `dead_letters` and incident state. Never update historical
  quote/forecast values in place.
- **Reconciliation:** each officially completed game enumerates its frozen
  picks; if exact verified final cannot be found, record PENDING plus reason,
  retry with bounded backoff, alert when overdue. DNP is a verified void,
  not a synthetic zero or a losing under. No goblin/demon threshold grades.
- **API:** return NBA/NFL unified schedule and current health in one
  versioned response, including provider age for each game; use server-sent
  events or 30-second API polling on clients. ESPN browser-direct remains
  optional fallback, not the only live source.
- **Secrets/quota:** only server holds keys; per-provider budget ledger and
  hard ceilings, free score sources first, quota failures visible. Underdog
  ingestion requires its own genuine supported/authorized line source.
- **Migration:** dry-run import all original NBA/NFL ledgers and their checksums,
  reconcile every identity and grade with the existing exports, then run old
  and new collectors in **shadow comparison** before shifting reads/writes.
  Do not disable legacy grading or delete JSON while any records differ.

## Prioritized execution and release gates

### P0 — enforce current data safety, immediately
1. Land independently tested per-game live merge and known NBA team-code
   display reconciliation (this branch).
2. Cap automatic paid re-polling (this branch).
3. Run read-only nightly proofs of the deployed site with actual schedules,
   source timestamps, live game observations and frozen projections.
4. Audit all existing workflow failures and identify jobs whose queue groups
   displace pretip capture or verified settlement. Do not indiscriminately
   split groups while same data files still have competing publishers.
5. Keep one official pregame line per displayed market; retain all historical
   versions for audit and independent graded research.

### P1 — persistent storage and worker, before friend release
1. Deploy Postgres and one supervised scheduler **only after hosting is
   selected and credentials configured**; provide migrations, backup/restore,
   migrations rollback, source adapter contracts and test isolation.
2. Build idempotent import from immutable historical NBA/NFL snapshots;
   verify counts, IDs, timestamps, status and final values exactly.
3. Run worker and old GitHub publishers in shadow mode; compare every
   official NBA/NFL fixture and original line capture.
4. Cut live polling to backend after validated source coverage. Use one
   queue for final settlements and a separate bounded queue for research.

### P2 — settle and simplify
1. Migrate capture, official final boxscore reconciliation and grade outbox
   atomically; compare outputs to preserved original ledgers.
2. Implement authenticated Underdog standard-line collection; until then do
   **not** claim full Underdog support.
3. Disable redundant cron/main-writer workflows by category, in stages.
   Retain GitHub Actions for code CI, research model training and deployments.

### External beta acceptance — all required, no greenwashing
- **Three consecutive complete NBA game nights and an NFL game cycle** run
  without manual repair. Grade or verified void **100% of frozen eligible**
  picks after official final is available; every unresolved one carries an
  explicit source/retry state, never a fabricated grade.
- Every fixture appears before tip whether or not its model/provider has props.
- Active game's source age and coverage are observable in the actual public
  app. Missing scores/stats are visibly degraded; no false 0 or stale live.
- Original frozen standard price, projection, direction, timestamp and grade
  remain immutable across concurrent producer failures, process restarts and
  backfill. Duplicate line versions do not inflate primary hit rate.
- Automated alerts and backoff/retry for every missed live source and overdue
  final; no human has to request the next update.
- Quota checks remain within approved budgets; successful disaster restore,
  failure injection and rollback rehearsals.
- Canary actual iPhone browser on mobile network, not solely cloud/headless
  simulated fetch. Confirm deployment version and cache invalidation.

**Status:** P0 code fixes in PR; architectural migration and sustained
production passes are still pending. This is not a release certification.

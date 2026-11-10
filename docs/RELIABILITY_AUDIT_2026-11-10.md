# Sports-Bot reliability audit — 2026-11-10

Scope: read-only review of the published GitHub Pages artifacts, key GitHub Actions workflows, and the latest 100 Actions run results. This is **not** a certification that every source or model is operational; all missing evidence remains explicitly unverified.

## Verified repaired issue

- Dame's Picks integrated UI CI previously failed because the test assumed `pendingReason` must be nonempty even when the authoritative `pp_grading_pending_2026.csv` has only its header and `grading_health_2026.json` reports zero pending picks. The test was changed to require pending cards to equal the published pending count, without inventing pending grades.
- The new layout-specific test passes, and the integrated CI passed after the repair.
- Independent GitHub Pages layout verification passes. A separate live verifier is scheduled to catch regressions.

## Evidence from latest checks

| Component | Observation | Required next action |
|---|---|---|
| PrizePicks source | Provider snapshot in `ai_prizepicks_quick_join.json` was from 01:31 UTC while its 16:16 UTC join was `STALE_OR_UNVERIFIED_SOURCE` with zero matched games | Restore verified fresh pregame quotes; preserve credit budget; reject stale offers |
| NBA AI + line join | Zero fresh verified matches in saved quick join | Verify same event, player, market, provider, threshold and pre-tip freeze; do not substitute AI-only cards as wagerable |
| Pregame capture | `tonight_capture_gradeability.json` marked `CAPTURE_INCOMPLETE` and game records show `NO_CAPTURED_PROVIDER_LINES` | Recover only archived genuine quote snapshots; add pretip missing-market alert and immutable freeze receipt |
| NBA production gate | `production_readiness.json` marked `DEGRADED` with line and published pick card gaps | Keep NOT_READY until actual standard props and frozen projections are visible |
| NBA feed health | Recent `phase1_feed_health` reported `ODDS_STALE` and `TRACKER_STALE` | Distinguish pregame, live and postgame; source recovery must have bounded timeouts and freshness limits |
| NBA grading | `ai_forecast_coverage_audit.json` marked `VERIFIED_FINAL_ROWS_OUTSTANDING` | Recover verified final boxscores and grade *frozen standard quotes only*, separately track AI-only forecasts |
| NFL grading | `grading_health_2026.json`: 456 final candidates = 440 graded + 0 pending + 16 verified voids; 60 settled standard offers, 26 wins | Continue checking exact frozen-identity joins and standard-only grade math; never incorporate 379 alt-tier historical grades |
| Public site deployment | GitHub Pages showed successful publication of layout commit; repeated cancelled builds in high-frequency push history | Prefer controlled source-change deploy; verify actual public HTML and track cancel frequency |
| Automated checks | Latest 100 workflow runs included failures in source readiness, AI join, feed health and model readiness, not just UI | Group alarms by fault domain to avoid hiding root cause behind dozens of red workflows |

## Redundancy and recovery contract

| Strand | Primary | Backup or recovery | Immutable safety rule |
|---|---|---|---|
| Schedule and games | Official/current schedule source | Independently published ESPN/verified scoreboard + reconcile IDs | Do not invent games, team mappings or start times |
| Standard lines | Authenticated standard PrizePicks/Underdog observations | Last *verified pre-tip* archived quote for display and later historical grading | Never treat stale quote as fresh; goblin/demon cannot enter official win rate |
| Projections | Current model | Last immutable pregame forecast, clearly labeled historical; AI-only research when no quote | Never retroactively refit frozen projections |
| Pregame snapshot | Atomic frozen line + model receipt | Replay previously verified snapshot from immutable archive | Source/price/player/game/time/version identity must match exactly |
| Injury and depth | Verified injury / current roster | Last timestamped reference as context only | Outdated injury data may not silently alter frozen picks |
| Live tracker | Verified fresh ESPN player updates | Last observed snapshot labeled STALE and independent scoreboard state | No live/pace claim for an expired observation |
| Final stats | Verified final game/player boxscore | Independent official/secondary final source + cross-check | No final settlement without verified player and stat identity |
| Grading | Deterministic saved quote vs final stat | Replay immutable archive with idempotent reconciliation | No artificial win, loss, push or void; account for every frozen pick |
| Web UI | GitHub Pages | Last known good artifact and error/partial-state display | No invisible "success" for missing cards, quotes or stats |
| CI/deployment | Source/unit/browser tests + Pages publish | Read-only live HTTP verification and explicit failing gate | A passing git commit is not proof of public deployment |

## Safeguard policy

1. **Detect:** timestamp every source and classify freshness, completeness, and source verification.
2. **Contain:** use stale read-only displays, disable affected actionable directions, and retain saved research.
3. **Recover:** bounded retry + jitter and verified secondary feeds where supported; do not exhaust paid credits.
4. **Reconcile:** compare expected games, players, frozen record identities, and final grades to produced outputs.
5. **Verify:** unit + browser + production URL checks; confirm source commit/asset where possible.
6. **Escalate:** a missing source remains degraded until verified; never turn a red gate green using synthetic defaults.

## Implementation in this pass

- Repaired NFL pending assertion, preserving real zero-pending behavior.
- Added and exercised Dame's Take placement check and live public HTML verifier.
- Added `iphone_bot/audit_failure_domains.py`: no-cost read-only multi-domain snapshot auditor.
- Added `.github/workflows/cross-domain-reliability-audit.yml`: scheduled every 30 minutes, manual dispatch, failure/summary for critical conditions.

## Remaining work — not yet marked fixed

1. Restore fresh verified standard market captures and per-game coverage before kickoff; avoid provider billable calls when no eligible games exist.
2. Restore a correctly keyed NBA saved line+AI join; preserve distinct AI-only research, stale quotes, and actionable verified plays.
3. Recover real NBA grading backlogs and separate unresolved player DNP, missing stats and mismatched frozen identities.
4. Fix current live player feed freshness/coverage and ensure the tracker uses explicit `STALE` rather than an invented zero.
5. Reduce redundant push-driven GitHub Pages cancellations and tie deploy verification to a specific source version.
6. Expand failure-injection tests for upstream outage, stale/partial provider boards, duplicated frozen picks, skipped final boxscores, timezone shifts, and failed deployment.
7. Audit each workflow's trigger, error propagation, permissions, write conflicts and cost guardrails before calling the whole bot stable.

**Status: DEGRADED.** There is no basis for claiming 100% reliability until these remaining gaps are resolved and observed over multiple slates.


## November 10 follow-up — verified recovery and remaining blockers

**Newly confirmed safeguards**
- Independent verified standard-line and pregame-AI comparison refreshed: 209 research-only matched offers across six games; excludes one-sided, demon, goblin, and unverified tiers. This is *not* a calibrated betting model.
- Immutable separate research capture `docs/standard_quote_ai_research_archive.json`: 209 receipts, one record per exact player/game/stat/standard threshold. The earliest captured projection is retained; replay and outages do not multiply records or rewrite frozen values.
- Research-only settlement `iphone_bot/grade_standard_quote_ai_research.py` and scheduled workflow independently reconcile verified NBA final-player rows to those receipts. Outcomes are HIT/MISS/PUSH/VOID/NO_LEAN/UNSETTLED_RESEARCH, separate from official model hit rates. Missing or conflicting final identities stay unsettled; retries cannot rewrite a settled result.
- No-op archive and grading replays preserve the old artifact byte-for-byte, avoiding unnecessary commits, Pages rebuilds and provider usage.
- Regression tests cover moved prices, alternate tiers, stale/future snapshots, duplicated quotes, verified final matching, DNP voids, push, conflicting finals and repeat-run stability. Latest independent grading and join jobs passed.
- The pregame capture health report now explicitly distinguishes unmatched validated model locks from separate research receipts. For the November 10 Eastern slate: 212 standard source quotes, **63 without exact primary frozen-model matches**, of which **60 have separately preserved research receipts** and **3 have no AI forecast**. These are *not* silently promoted to validated primary picks.

**Unresolved, do not mark production green**
1. The 63 exact-primary-model gaps remain, including 36 legitimately moved original prices, 24 AI-only cases with no validated freeze, and 3 markets with no matching archived AI forecast. The new separate research receipts do not rewrite the historical primary-model denominator.
2. The independent source board is marked partial; fresh 209 matched quotes do not prove complete provider coverage.
3. `production_readiness.json` is DEGRADED, and `tonight_capture_gradeability.json` deliberately remains CAPTURE_INCOMPLETE.
4. The GitHub Pages repository remains in legacy branch publishing mode. The controlled Actions publisher cannot change the Pages setting with its token (HTTP 403). A repository administrator must switch **Settings → Pages → Build and deployment → Source → GitHub Actions**. Until then, cancelled branch builds may recur.
5. Existing NBA retrospective/final-grade coverage and per-player live observations require separate final-boxscore and active-game checks. No postgame research grades exist yet for these future games.

**Invariant:** no source fallback, archived research result, or completed GitHub Actions job is proof of a live, validated betting pick. Standard original lines and frozen identities control all settlement; alternate tiers never count.

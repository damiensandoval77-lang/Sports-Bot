# PARTIAL — Sports-Bot repair cycle

Started 2026-11-13T18:25:18+00:00; evidence collection ended 2026-11-13T18:39:04.177050+00:00 (826 seconds). Six finding groups recorded; one repaired and independently verified in production. The full execution contract is not complete.

Pinned main: `872c18db624bbc886191ac2dfa15f5c84ea2133f`. Static-verified main: `4ca255595d2b9a3050cabdd8b08f7477cb3a14fa`. Deployed release: `dp-public-qa-labels-20261113-r36`.

## Findings and repair log

### D1 — Mutable actions in privileged health controllers (medium)

**Outcome:** REPAIRED_HOSTED_PRODUCTION_VERIFIED.

Root cause: Six checkout/setup/upload uses loaded mutable version tags in workflows with repository/Actions/issue write capabilities.

Before: External release tags could change executed code independently of repo review.

After: All six references use verified commit SHAs; regression rejects mutable external actions in both controllers.

Tests: 90 heartbeat/readiness/recovery tests + 7 critical contracts passed locally; all four CI checks passed including 221 pipeline contract commands.

Verification: Both production controllers downloaded pinned revisions, performed monitoring/recovery and uploaded artifacts. Final gates correctly remained red for source/coverage failures; public readiness read back at 18:35 UTC.

Files: `.github/workflows/pipeline-heartbeat.yml`, `.github/workflows/production_readiness.yml`, `tests/test_critical_production_repair_contracts.py`.

[PR #425](https://github.com/damiensandoval77-lang/Sports-Bot/pull/425) · [Merge](https://github.com/damiensandoval77-lang/Sports-Bot/commit/666a88ea6661ff163cd95714bdc00f4f2b6c8c6b)

Production runs: [43483508923](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43483508923), [43483508534](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43483508534).

### D2 — Primary NBA forecast coverage remains incomplete (high)

**Outcome:** BLOCKED_BY_MODEL_ELIGIBILITY_EVIDENCE.

Root cause: Six players have only 3-7 qualifying same-team opportunity-history games under the existing eight-game primary eligibility gate (diagnosis carried from prior cycle; unchanged source code).

Action: Rechecked exact current missing offers and free official schedules; no post-tip predictions or unvalidated research predictions promoted to primary. Existing model recovery was active/recent and was not duplicated.

Counts: current offers: 371, matched: 355, missing: 16, archived standard thresholds without primary: 28, separate research receipts: 12, no ai receipt: 16.

### D3 — PrizePicks snapshot became stale (high)

**Outcome:** BLOCKED_NO_PAID_REFRESH_AUTHORIZED.

Root cause: Last authentic source observation 17:19:22 UTC exceeded 60-minute freshness gate; controller retained 90-minute paid collector cooldown.

Before after: Snapshot retained with original observation time; 73 minutes old at 18:32 check. Readiness moved from9/10 to8/10.

Action: Verified published timestamp and recovery skip reason. Did not change thresholds, backdate source time or call paid provider.

### D4 — Native branch Pages cancellation races persist (medium)

**Outcome:** BLOCKED_PAGES_ADMIN_SETTING.

Root cause: Pages is still configured for branch publishing; repository-level source setting is outside available connector mutations.

Workaround: Verified successful native deployment and exact public release/assets; controlled Pages workflow correctly uses native-source verification and skips deploy-pages.

Required action: Repository Settings > Pages > Build and deployment > Source > GitHub Actions. Requires authenticated repository admin settings access.

Cancelled runs: [43483972358](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43483972358), [43483593914](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43483593914), [43483465178](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43483465178), [43482974937](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43482974937), [43482959018](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43482959018).

Successful native runs: [43484060163](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43484060163), [43483614679](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43483614679), [43483506681](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43483506681).

### D5 — Four older open PRs have unresolved merge conflicts (medium)

**Outcome:** UNRESOLVED_NOT_MERGED.

Action: Fresh read-only git merge-tree comparisons recorded exact conflict paths. Clean merge trees for272,132,72 do not prove relevance or production safety. No obsolete root UI or unvalidated short-history model was merged.

Limitation: Full semantic repair and replay of every historical branch was not completed in this cycle.

### D6 — Repository-wide workflow hardening remains incomplete (medium)

**Outcome:** UNRESOLVED.

Action: All definitions statically audited. Six critical references pinned. Remaining broad changes were not deployed; some source workflow edits can trigger provider collectors and need trigger/cost-safe validation.

Limitation: Zero syntax errors is not a clean security/dependency bill of health. Exhaustive package-vulnerability and git-history secret scans were not completed.

Counts: mutable action references: 384, architecture warnings: 45, scheduled workflows: 83, workflows: 174.

## Inventory, tests, and workflow evidence

426 active branch heads and 425 PR tips fetched and compared. Seven pre-existing PRs remain open; #307, #249, #135 and #3 have fresh merge conflicts. [Exact conflict paths](open-pr-conflicts.json). The HTTP inventory script stalled and was interrupted; full local Git ancestry comparison provided the fallback. Deleted unreachable refs and semantic execution of every historical revision are not covered.

All 174 definitions were statically audited: 1,231 tracked files, 571 Python AST checks, 251 JSON parses, 38 JavaScript syntax checks, zero errors, 45 architecture warnings. Six mutable action references were removed; 384 remain. This is not an exhaustive vulnerability or history-secret scan.

598 recent run observations across 81 workflows were reconciled with the preceding complete per-workflow inventory. That sample has 354 successes, 85 failures, 155 cancellations, one skip and three in-progress states at sampling. These are historical observations, not 85 current defects. All 83 scheduled definitions have prior observed runs. Manual nba-backtest-real-market.yml has no run evidence. [Every workflow, triggers, latest evidence, and recent failed/cancelled IDs](workflows.md). Older per-workflow histories were retained rather than re-fetched for the remaining 93 definitions.

All 97 targeted local tests passed. Four final PR checks passed, including 221 pipeline-contract commands. The first PR attempt failed because the new regression caught one remaining readiness upload tag; that was patched and retested before merge. Production heartbeat 43483508923 and readiness 43483508534 used the pinned actions and uploaded evidence successfully, then correctly failed their final data-quality gates. Unified run 43482926333 successfully pushed its degraded JSON; its nonzero publication-step exit reflects the quality result, not a failed push. [Detailed repair evidence](repair-evidence.json).

## Data and grading

NBA: all nine games have saved standard quotes and forecasts. There are 607 archived standard quotes, 355 of 371 current offers matched to eligible primary forecasts, 28 archived threshold gaps (12 with separate research receipts, 16 without any AI receipt), 904 AI-only records, and 582 line-backed records. None of the research receipts were promoted to primary to force a pass.

Missing current forecasts: Patrick Williams 2, Jaylon Tyson 2, Jalen Suggs 3, Ivica Zubac 3, Max Strus 3 and Keegan Murray 3. Exact markets and thresholds are in [capture evidence](public-tonight_capture_gradeability.json).

November 12 NBA: 388 captured AI forecasts = 332 graded + 56 verified DNP exclusions; zero unaccounted captured records. The separate research ledger has 327 records = 318 settled + 9 void, zero overdue. NFL has 135 standard grades including 3 pushes; 52 wins / 80 losses = 39.39%, zero standard pending. Historical alternate tiers remain excluded: 932 graded and 4 pending. Missing authentic pretip evidence was not reconstructed or converted into grades; the number of never-captured markets is unknown.

Fresh free ESPN reconciliation matched all nine NBA event identities and tip times. NFL WAS 24–NYG 21 and all 18 published player rows matched the official summary. The NBA fixed season calendar has 1,200 fixtures; NFL has 272. NBA Cup TBD fixtures are not fabricated.

## Public deployment and limitations

Public JSON was independently read at 18:35 UTC. Readiness is 8/10 at its 18:32 check: primary coverage remains incomplete and the authentic PrizePicks source is 73 minutes old. No paid refresh, stale timestamp rewrite or freshness-threshold relaxation was used. Native Pages deployment of the repair merge succeeded in run 43483506681. Later native success 43484060163 does not eliminate cancellation races.

[Phone artifact](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43482050735/artifacts/14066455467): checked 18:24:19 UTC and downloaded/reviewed this cycle; 390×844 Chromium emulation, nine checks passed, 393 cards, no JavaScript exceptions, six exact asset matches. This precedes PR #425; that PR changes workflows only, and its production execution was separately verified after merge. It does not prove physical iPhone/Safari or active-game pacing.

Full Underdog capture-to-grade coverage, actual 30-second updates during live games, and a complete 72-hour clean production window remain unverified. No active games were present during these checks. No Replit, paid provider call, secret change, destructive remote action, fabricated forecast or fabricated grade was performed by this cycle.

The existing two-hour automation remains enabled. No duplicate task was created. Please notify Damien through enabled ChatGPT mobile notifications; delivery has not been confirmed.

# Active repair cycle — PARTIAL

Start 2026-11-14T00:24:45Z; end 2026-11-14T00:36:12.200444+00:00; duration 687 seconds. Pinned main `ff0eca4b68296f7e505261503f799c95f181cc4f`.

## Repair and before/after evidence

High: a valid but older raw-GitHub live snapshot was returned immediately, hiding newer Pages observations. A failing regression reproduced this selection defect. PR [433](https://github.com/damiensandoval77-lang/Sports-Bot/pull/433), head `0caf839e8eaba6c3ecc32603fbf39ddfc3587958`, merged `96782d8907d6d9eda1e0b7eeb1bcd63720eb3248`, now requests both bounded public snapshots and chooses the newest validated timestamp. No paid/provider quote polling was added. Changed: docs/dames-picks/index.html; feeds.js, live_direct.js, dames_take.js, provisional.js, short_history.js and release.json coherently versioned r40; tests/test_feed_deadlines.cjs adds three source-selection cases. 16 targeted tests passed; all ten PR checks passed. Broad local suite 162 passed and one browser executable unavailable; hosted browser CI passed. 41 Python collector/merge/browser tests passed.

Operational score failure: run [43533398047](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43533398047) originally rejected stale/no-score upstream snapshots with ValueError. Same-run retry job 132259042658 passed after official data became available. Published NBA scores reconciled with official source for both active games. Original browser run [43533875703](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43533875703) failed with two missing scores, including its retry. Later [43534983873](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43534983873) passed: two active NBA games, zero missing games/scores/players; NFL zero missing and no active games. Provider recovery occurred independently too; this is not proof that cache priority alone caused the entire incident.

Exact deployed r40 verification status: True. Browser evidence JSON is included when complete. Earlier r39 Chromium/WebKit artifacts at 00:16 UTC are labeled BEFORE and are not counted as r40 proof. Phone width is emulated, not a physical iPhone. Thirty-second timer exists, but direct provider probe returned no data; 30-second upstream updates are not certified.

## Coverage and grading

Nine NBA games today; full fixed season 1200 games. NFL season 272 games. Upcoming standard offers 299; primary matched 285; missing 14. Missing players: Patrick Williams (3 history games), Nic Claxton (2), Jaylon Tyson (6), Jordan Poole (6), Max Strus (4), Keegan Murray (4), Dylan Cardwell (4). No eligibility relaxation or invented pretip data.

Archive: 748 standard thresholds, 691 line-backed forecasts, 904 AI-only forecasts; 60 unmatched exact thresholds comprising 9 moved lines and 51 never-primary markets. Of the 60, 30 have separate research receipts and 30 have none. All nine games have some source quotes, AI and line-backed models; that does not mean full market coverage.

November12 NBA: 327 captured PrizePicks records =318 settled+9 void; zero overdue. AI388=332 graded+56 verified DNP; zero unaccounted captured AI. NFL135 standard grades including3 pushes;132 decisions,52wins/80losses,39.39%;zero standard pending. 932 alternative grades and4 alternative pending remain excluded. Missing uncaptured historical pretip evidence cannot be recovered truthfully; count unknown.

Player reconciliation compared an earlier published snapshot with a later upstream observation:69 rows,16 changed totals. These are asynchronous live observations, not proof of bad grading. The browser subsequently showed current player data; a guaranteed 30-second provider cadence remains unverified.

## Inventory, workflows and exceptions

433 branch heads plus432 PR-tip refs fetched and locally compared at initial pinned main (origin/HEAD excluded). PR433 adds a branch and tip after inventory. No prior open PR required carry-forward. The API inventory separately recorded433 branches plus6 non-head historical tips,51 comparisons succeeded and388 HTTP403 failures. Full local Git divergence is the fallback, not complete semantic testing of every revision.

All176 workflow definitions statically checked:0 errors,45 PRODUCTION_UNIT_TEST_GATE warnings and385 mutable action references. These are unresolved architecture/hardening observations, not385 proven vulnerabilities. See workflows.md for every definition and its latest sampled run; no sampled run is marked UNVERIFIED. Recent sample100 runs is not exhaustive history. Tests skipped in scheduled collector are intentional PR-only regression steps, not failed executions.

Heartbeat [43533211707](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43533211707): capture_integrity, live_scores and live_players failed; automated recovery skipped because of active/recent-run backoff. Readiness [43533272999](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43533272999) failed live/coverage gates. Unified integrity [43534983890](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43534983890) remains failed; do not suppress capture gaps. Native Pages runs43533940777,43533898660,43533864714,43534982167 cancelled; eventual public release verification is separate. No stuck-job diagnosis is inferred merely from in-progress status.

## Unresolved blockers

B1 primary-model/history and archived threshold gaps remain. B2 Pages administrative switch remains unavailable: owner must select GitHub Actions under Settings > Pages and verify controlled publication. B3 browser-direct provider access/cadence remains unproven; public snapshots are the fallback. B4 full workflow histories/historical semantic audit remains incomplete. Full Underdog quote ingestion and every model's injury/matchup calibration were not independently certified this run. Gates remain honest.

No paid API calls, Replit, secret changes, destructive operations or fabricated captures/grades. This run is PARTIAL, not fully hands-off readiness. Please notify Damien through enabled ChatGPT mobile notifications; delivery is unconfirmed.

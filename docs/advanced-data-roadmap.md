# NBA Bot — Advanced data improvement queue
Created: 2026-11-07. Research only; not an automated betting strategy.

## Delivery order and acceptance gates

- [x] **P1 importer and provider-request plan built — Licensed WOWY teammate on/off and lineup impact.** PBP Stats documents on/off, lineup, and playing-time API endpoints: https://api.pbpstats.com/docs. Build a strictly pregame, player-ID-matched importer with provenance, rights flag, minutes and game counts. Do **not** enable API network calls, upload historical third-party feeds, or modify current predictions until API authorization/licensing for this use is verified. Freeze and grade new shadow candidates.
- [ ] **P2 — Potential assists and passing opportunities.** Verify authorized tracking provider and per-player ID coverage, include passes/potential assists, then run prospective AST shadow.
- [ ] **P3 — Rebound chances and opponent missed shots.** Find authorized tracking source with rebound chances/contested chances and build REB/PRA challenger.
- [ ] **P4 — Pace, efficiency, and opponent possession data.** Validate current opponent V2 using legitimately sourced possession data and rolling team efficiency; compare to Combined on future dates.
- [ ] **P5 — Injury-triggered lineup-aware forecasting.** Integrate verified NBA injury statuses with licensed recent lineup splits, recompute from preinjury baseline, and keep all versions for grading; avoid unadjusted displayed probabilities.
- [ ] **P6 — Play-by-play/historical fallback and provider monitoring.** Investigate authorized PBP provider (including SportsDataverse/hoopR rights), coverage, price, ID mapping, freshness, caching and quota.
- [ ] **P7 — Research charts.** WOWY with/without per36 and both sample sizes, model MAE by prospective date, and probability reliability diagrams only on settled independent markets.

## Provider access blockers

- PBP Stats API docs are discoverable: https://api.pbpstats.com/docs
- Its pricing, authentication, permitted automated extraction and betting-related usage have **not been verified**; endpoint visibility is not a data license.
- NBA statistics have explicit use restrictions, including gambling-related uses: https://api-hub.nba.com/termsofuse
- NBA.com tracking pages do not by themselves grant automated dataset downloading: https://www.nba.com/stats/help/faq
- No API credentials or third-party data rights have been confirmed. **Automatic PBP Stats ingestion remains disabled.**

## Universal validation gates

1. Source rights and permitted purpose confirmed before ingestion.
2. Resolve exact player ID, teammate ID, team and season (no approximate identity matches).
3. Every observation must have a verifiable publish time and a prior-data cutoff *strictly before* the game, without target-game leakage.
4. Require sufficient on/off exposure, not merely a few games. Report with/without counts.
5. Keep original pregame numbers immutable; shadow challenger runs in parallel.
6. Grade against the same eventual final player total and the *same frozen line*.
7. Only consider promoting models after enough independent future game dates; never treat simulated probabilities as calibrated.

## Implementation checkpoint (2026-11-07)

P1 now includes:
- Provider-specific, network-disabled request plan for player/teammate ON vs OFF (`iphone_bot/pbpstats_request_plan.py`).
- Local authorized export importer (`iphone_bot/import_authorized_onoff.py`) with exact player/team ID validation against current 2026-27 roster.
- Mandatory separate manually reviewed usage permission reference, source observation timestamps and minimum exposure.
- Private, gitignored provider-data destination (`data/nba/private/lineup_onoff_research.json`).
- Research snapshot and exact-line grading, currently inactive with no real licensed rows.
- Automated test coverage for importer, API request plan, no lookahead and population rules.
- Setup: `docs/wowy-provider-setup.md`.

**Not finished:** provider permission for prop analytics, actual response mapping and current-season data access, source-specific historical cutoff, a successful end-to-end live provider fetch, and verified CI run. No public source totals have been reclassified as user-authorized data.

## PBP Stats API example integration checkpoint (2026-11-07)

The provider-owned GitHub notebook confirms two separate WOWY requests: target player AND teammate ON FLOOR, and target player ON while teammate OFF FLOOR. The provider OpenAPI specification (https://api.pbpstats.com/openapi.json) confirms `FromDate` and `ToDate` on the WOWY endpoint.

Added:
- `iphone_bot/pbpstats_wowy_adapter.py`: validates provider-style `multi_row_table_data` and exact `EntityId`, converts `Points`, `Rebounds`, `Assists`, and `SecondsPlayed` or `Minutes` into per-36 splits.
- Exact ON/OFF request provenance including `FromDate` and `ToDate` must accompany each split. Undated post-game aggregates cannot be relabeled as pretip samples.
- `iphone_bot/tests/test_pbpstats_wowy_adapter.py`: synthetic provider-schema mapping and lookahead rejection tests, added to both model workflows.
- Fixed invalid variable reference in `iphone_bot/lineup_onoff_research.py` which would have raised an exception when validating on/off groups.

Remaining for P1: Confirm authorized ongoing use in prop analytics, validate independent game-level with/without coverage tied to each query, and obtain a permissible production export. Public probe HTTP 200 proves technical accessibility, not provider authorization or actual historical sample quality. No live predictions changed.

## P1 end-to-end transport checkpoint

The technical response pipeline is connected: `iphone_bot/assemble_pbpstats_wowy.py` accepts two independently obtained, authorized, properly date-bounded provider JSON responses, calls `pbpstats_wowy_adapter.normalize_pair`, then passes the resulting normalized data through `import_authorized_onoff.validate`. Approved data is stored only in gitignored `data/nba/private`, after which pregame research can snapshot licensed teammate OUT splits with the original Combined AI unchanged.

The build runs synthetic end-to-end tests through the new `iphone_bot/tests/test_assemble_pbpstats_wowy.py` in both GitHub research and trained-board workflows. These tests verify software behavior, **not** current-season game availability, legal data permissions, or model effectiveness.

Still blocked: explicit permission for this use case, an actual 2026-27 authorized provider feed, independently verified per-split game dates (not guessed), and confirmation the latest new CI checks passed. Until these clear, live provider ingestion stays disabled and WOWY prospective coverage remains zero.

## 2026-11-07 current-season probe and full integration CI verification

- **Actual API response, current season:** `docs/pbpstats_current_season_probe.json` shows both strict `2026-27` date-bounded teammate ON/OFF requests succeeded with HTTP 200 and one uniquely matched target `EntityId` each. Core Points/Rebounds/Assists/Minutes/SecondsPlayed fields exist in both. These are metadata diagnostics; no third-party stat rows were copied.
- **Offline source adapter validated:** `docs/pbpstats_wowy_validation_status.json` now shows `PASSED` for five test modules (3+5+4+6+4 tests). Fixed two undeclared WITHOUT-group variables in `iphone_bot/lineup_onoff_research.py` discovered by real CI.
- **Source game-level qualification remains unverified.** The WOWY aggregate player record does not expose individual game dates. A season/date filter and plausible exposure minutes are not enough to prove independent ON/OFF game counts. The importer correctly continues to require independently verified underlying game participation or lineup observations.
- **Rights remain unverified.** Public PBP Stats API docs and successful unauthenticated API response do not establish authorization for recurring betting-model use, caching, storage, or publishing. No scheduled on/off provider-stat ingestion, real licensed samples or production AI changes are enabled.

## P1 actual 2026–27 source data audit (2026-11-08 UTC)

Began verifying *real* public historical game-level ON/OFF exposure, not just response schema. Details: `docs/pbpstats-real-data-research.md` and `docs/pbpstats_onoff_coverage_probe.json`.

- Curry/Green: 7 games, 175.03 min together; 4 games, 20.55 min apart. OFF sample insufficient.
- Brunson/Hart: 7 games, 205.13 min together; 7 games, 66.57 min apart. Both source minutes reconcile within the current 3%/3 minute threshold, but OFF exposure is insufficient.
- Wagner/Banchero and Trae Young/Anthony Davis: API requests encountered HTTP errors. No numeric assertions or model adjustments derived from these.
- Encountered authentic zero-duration and overlapping possession intervals; now correctly ignores zero-second intervals and unions overlaps.
- The provider research probe is manual-only to avoid repeated third-party calls on unrelated commits while provider limits/rights remain unclear.
- P1 cannot yet be marked complete: no qualified independent 5-game/120-minute ON *and* OFF sample and no live model benefit measured.

## Model accuracy improvement sprint — 2026-11-08

**Why:** The latest immutable grading (`docs/grade_quality_scorecard.json`) shows Combined AI at 282/592 (47.64%) and -13.38% hypothetical paper ROI on the recorded prices. Only two independent game dates exist; raw probabilities are not calibrated (original model 62.68% mean estimated vs 45.28% actual in 318 graded observations). This is a losing sample, not a demonstrated edge.

**First model improvement delivered:** `iphone_bot/rebound_shadow_v1.py`. New fixed, conservative rebound-rate challenger:
- Strict completed same-team prior history, >=8 qualifying games and duplicate-date conflict exclusion.
- Predicted minutes from a frozen pregame input or prior-game-only fallback; reject recent minutes SD above 8 and low-minute recent rotations.
- Exposure-weighted season rebounds per minute (65%), last-five median rate (35%); 30% blend toward historical opportunity estimate, maximum 12% deviation from frozen Combined AI.
- Pre-tip immutable field `rebound_shadow_v1` in `docs/projection_upgrade_ledger.json`; grade on identical player/event/market and exactly the same frozen sportsbook line as the original Combined AI. Results appear under `rebound_shadow_v1` in `docs/projection_upgrade_status.json`.
- Research dashboard now displays future paired REB MAE, correct side counts and eligibility, without claiming a live edge.
- Both new standalone tests and the full research integrity suite verified PASSED in GitHub Actions (5 + 23 tests, `docs/rebound_shadow_validation_status.json`).
- **Current genuine REB V1 results: zero newly graded markets.** It was created after the earlier settled games. Do not reconstruct an in-sample prospective hit rate or change production projections.
- Existing prospectively frozen *generic opportunity* REB challenger on one game date: baseline 2.107 MAE vs opportunity 2.037 on 87 paired markets; on 67 exact-line eligible calls, Combined 26 correct vs opportunity 31. Descriptive only; cannot be attributed to the new rebound V1 or promised for future games.
- Existing pregame assist-specific shadow on 42 assists and one date: Combined MAE 1.893 vs assist challenger 1.886, but directions 25 vs 24, respectively. **Do not promote** or assert it improved win rate.
- On-screen model leans are raw directions, not verified profitable picks; misleading simulated percentages and EV ranking were removed in the prior grading-integrity sprint.

**Next gating milestones:** lock REB V1 projections on multiple *future* NBA game dates, grade on the exact original line without retroactive regeneration, compare paired MAE and win rate against original Combined, review exposure and injuries, and only consider a change if the candidate improves held-out independent multi-day performance (not merely this two-day grading snapshot). Preserve all losing grades; no production promotion until independently justified.

## P2 / P3 player tracking opportunities (2026-11-08)

Implemented **research-only** pipeline for the two additional features requested:
- **Potential assists:** authorized game-level tracked potential assists, the corresponding recorded assists, minutes, and per-player historical conversion. Avoids treating recorded AST as the opportunity denominator.
- **Rebound chances:** authorized per-game rebound chances, recorded rebounds, minutes, historical conversion, and strict prior-game exposure. Avoids treating traditional rebounds as chances.
- Both challengers are in `iphone_bot/tracking_opportunities_v1.py` with >=8 independent prior completed games, >=160 prior minutes, 65/35 season/recent opportunity rates, pregame expected minutes and conservative capped adjustments. Missing, future, duplicate, unlicensed or unstable samples are excluded.
- `iphone_bot/import_tracking_export.py` accepts a rights-reviewed provider CSV and writes only to gitignored `data/nba/private/tracking_opportunities.json`. Regular GitHub runners will not possess this private export.
- `iphone_bot/projection_upgrade_research.py` freezes alternative AST and REB predictions prospectively and grades both only against the *identical frozen sportsbook quote* and the original Combined AI. Results appear in `docs/projection_upgrade_status.json` under `tracking_opportunity_shadow`; the performance panel displays them.
- `docs/tracking_opportunities_validation_status.json`: PASSED 33 tests (6 dedicated model, 3 importer, 24 full integration). **No true tracking-derived live edge or hit-rate improvement has yet been measured.**
- **Rights limitation:** NBA.com's published Statistics terms restrict its data in connection with gambling, even when the endpoints are publicly readable. This work does *not* scrape NBA.com or suggest the public API access creates a license. A properly licensed independent data source remains necessary. See `docs/tracking-opportunities-setup.md`.

P2 and P3 are **built in code, source ingestion not yet active**. No live pick weights, grades or simulated probabilities were overwritten.

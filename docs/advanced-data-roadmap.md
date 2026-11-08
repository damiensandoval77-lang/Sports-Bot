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

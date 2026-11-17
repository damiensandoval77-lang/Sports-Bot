# Dame's Picks Concept #3 — exact visual target / integration gates
**Reference:** User-selected #3 player-intelligence mockup (1448 × 1086). The goal is fidelity, not a generic four-module redesign.
**Branch:** `feat/dames-concept3-match-20261117`
**Preview:** `docs/dames-picks/concept-3-preview.html`

## Implemented in the preview
- Near-black/deep-purple visual system with violet active navigation, thin panel strokes, softened purple header glow.
- Top horizontal navigation, score/date game ribbon, featured player portrait, next-game and key-prop cards.
- Horizontal Overview / Prediction Lab / Props / Splits / Matchup / Teammates / Trends / Game Log navigation.
- Exact reference hierarchy: four chart panels (recent bars, trend line, hit estimate ring, distribution histogram); four research panels (teammates, splits, matchup table, context); wide Prediction Lab and compact Dame's AI beneath.
- Responsive width checks at 320, 393, 768, 1448; functioning stat selector, navigational scrolling, AI-offline explanation, search fallback. Inline portrait and no remote asset/API calls.

## Deliberately not implemented
This is **not** a production deployment. The page is a pixel-target prototype, not a live sports/data adapter. All values in it are **illustrative**, prominently labelled. NBA/NFL/Tennis pipelines, frozen standard-line archives, grading ledgers, live trackers and existing board must not be changed by this preview. Do not link it in production until parity has been proven.

## Data mapping before promotion
1. Use existing normalized standard PrizePicks snapshots from `docs/dames-picks/feeds.js` (and the current export adapter) for line, projection, opponent, timestamps, direction, grades and Dame's Take. Only standard lines, not demon/goblin specials. Never invent a value.
2. Use immutable frozen pregame rows for model/line history; use independent ESPN/verified-final data for box score/grading. Display missing/stale as such; never substitute a historical hit rate for a matchup-conditioned hit estimate.
3. Player Intelligence uses canonical IDs, actual completed-game logs, season averages and minutes; label opponent defense, position grouping and teammate on/off as unavailable until reliable permitted sources and sample sizes exist.
4. Reconnect real NBA/NFL/Tennis selectors and the existing saved/live/tracker screens. This page targets the NBA player layout and must have sport-specific, non-fictional equivalents for NFL/Tennis.
5. Dame's AI must use actual verified records and clearly cite source/time. It stays visibly disabled in this preview.
6. Preserve nighttime pregame capture, fallback snapshots, live refresh, postgame grading, and protections against stale/partial data. No paid polling added.

## Promotion gates
- Compare rendered site against reference at 1448×1086 and iPhone width for consistent spacing/type/layout, then explicitly approve deviations.
- Run `python tests/verify_concept3_preview.py`; extend with browser E2E tests for actual real API response handling, no JS exceptions and safe fallback.
- Verify a complete game-day read path, a frozen forecast and its eventual grade, and no new cross-sport regressions on staging.
- Use one merged production website only; the old UI is retained until replacement is independently verified on the **deployed** URL and iPhone-visible display, not just by PR/CI.
- Remove the preview and migrate verified components into `docs/dames-picks/index.html` only after acceptance. Do not claim live success without live evidence.

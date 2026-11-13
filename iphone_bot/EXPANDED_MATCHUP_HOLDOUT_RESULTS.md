# Expanded matchup research — verified first pass (2026-11-09)

**Draft PR:** #109. **Historical Actions run:** 42694948667 (success).
**No production changes or automatic model promotion.**

The expanded model combines observed individual offensive-involvement
(FGA + 0.44 FTA + TOV per minute), Minutes V3, and strictly earlier reciprocal
team box-score pace/defensive production. Game-level opponent totals are NOT
individual guarding assignments. Fixed reference values and adjustment bounds
are research assumptions, not fitted weights.

## Frozen 2025-26 paired historical results

20,692 completed player-games across 149 dates, all scored on identical rows.

| Model | Points MAE | Points RMSE |
|---|---:|---:|
| Recent-scoring baseline | 4.9193 | 6.4234 |
| Offensive involvement only | **4.8761** | **6.3661** |
| Expanded involvement + minutes + opponent | 4.9155 | 6.4118 |

Expanded vs involvement MAE: **+0.0393 worse**.

- First 74 dates: baseline 4.8788; involvement 4.8381; expanded 4.8847.
- Final 75 dates: baseline 4.9557; involvement 4.9102; expanded 4.9430.
- 5,956 further player-games excluded for insufficient individual history.
- Reciprocal opponent team context present in the 20,692 evaluated samples.
- These are statistical errors, **not** PrizePicks hit rates or profit metrics.

## Feature-specific provenance / limits

- **Offensive involvement:** implemented as a proxy. Official USG% is NOT
  calculated; team-wide player-on-floor possession denominators are unavailable.
- **Minutes:** uses lagged, own-team historical minutes; lineup adjustments
  require separately verified pre-tip OUT reports.
- **Opponent:** prior completed reciprocal player-team boxes; no future game
  outcomes allowed. This effect was not independently calibrated.
- **Defense versus position:** G/F/C historical position source exists in
  `position_defense.py`; the expanded holdout has **not** verified all roles
  in an authorized, pregame-safe identity join, so its role factor remains off.
- **Injuries and teammate availability:** verified status gate exists, but
  postgame absence cannot be mistaken for a pregame injury report. No injury
  uplift was applied in this holdout.
- **NBAstuffer:** direct automated importing not implemented; suitable usage
  rights would have to be confirmed first.
- **20,000 simulations:** existing conditional Monte Carlo is unchanged;
  neither this uncalibrated historical improvement nor this historical
  prototype is a validated win probability.

## Next independent evaluation

Keep the involvement-only challenger as a benchmark, and **do not tune weights
using this 2025-26 holdout**. Pre-register any additional features and model
training on historical earlier seasons, then check untouched prospective
2026-27 pregame predictions against actual box scores and authentic locked
PrizePicks lines. Evaluate both MAE/RMSE and directional calibration by market,
recording feature availability and abstentions.

Prevent double-counting opponent effects when integrating with the existing
Combined AI; both pipelines may already contain opponent-aware forecasts.

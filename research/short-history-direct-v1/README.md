# Fixed direct monotone exceedance candidate

This new fixed model learns `P(actual > threshold)` directly instead of converting an absolute-error point projection into a residual probability. A monotonic constraint requires the probability to decrease as the threshold increases. Features remain lagged matchup pace/points allowance and own minutes/usage. Train: 2022–23 and 2023–24; isotonic calibration: 2024–25; diagnostic: 2025–26. Specification was saved before execution, with no post-result tuning.

## Results

Across 2,903 diagnostic player-games on 156 dates, all four synthetic-grid distribution gates pass against an independently calibrated empirical prior-average residual baseline using the same training seasons:

| Stat | Brier difference | Date-clustered 95% CI | ECE |
|---|---:|---|---:|
| PTS | -0.001786 | [-0.002579, -0.000938] | .00699 |
| REB | -0.002505 | [-0.003651, -0.001362] | .00740 |
| AST | -0.001868 | [-0.002981, -0.000686] | .01039 |
| PRA | -0.001104 | [-0.001925, -0.000245] | .00824 |

The 2025–26 season has already been inspected in other experiments. These are exploratory improvements, not an untouched confirmatory test. No calibrated betting-performance claim follows from synthetic thresholds.

## Genuine offered-line replay

Four players across one evening produced 14 archived offers with immutable pretip feature receipts and verified official final outcomes. Candidate probabilities were reconstructed now, after outcomes, and must never be inserted as original pregame forecasts. Brier versus baseline: PTS .30240 vs .24503 (5 offers), REB .38243 vs .38989 (3), AST .82108 vs .72115 (1), PRA .13128 vs .35913 (5). Results are mixed, correlated and too small for release inference.

## Next step and limits

Independent review and immutable future research capture under this distinct model version are warranted. Primary release is not approved. Half-integer lines only: no integer push calibration, no unobserved injury effect and no fabricated historical quote. Any future implementation must preserve current eligibility, identity, injury freshness and pretip provenance guards and avoid overwriting previous candidate receipts.

No production file, prediction, grade or user-facing percentage changed in this experiment. Historical source hashes, specification hash and full metrics are in result.json. Monotonicity asserted on all diagnostic threshold grids; existing seven feature chronology tests pass.

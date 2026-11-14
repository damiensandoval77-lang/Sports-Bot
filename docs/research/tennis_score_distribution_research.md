# Total Games distribution research

Offline research only. No live predictions, sportsbook thresholds, betting hit
rates, provider requests, production activation or public percentage estimates.

## Reproduction

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -m src.sports.tennis.score_distribution_research \
  --csv /path/to/valuebetennis-matchs-2026.csv \
  --output-dir /tmp/tennis-distribution \
  --as-of 2026-11-14T19:30:00Z
```

Source: [Valuebetennis season exports](https://www.valuebetennis.com/en/donnees.htm),
CC BY 4.0. Attribution: Valuebetennis, Tennis results and odds since 2021;
transformed score-only research. Source hash and import exclusions are recorded
in `total_games_distribution_evaluation.json`.

## Evaluation design

Whole UTC match days are partitioned chronologically 70%/15%/15% into training,
residual calibration, and untouched final evaluation. Records within 48 hours of
the next partition are purged. Final data also requires 48 hours before the
specified as-of time. That is an availability assumption, NOT observed result
publication provenance.

**Rolling-origin feature evaluation, not frozen-origin:** each match uses prior
histories available under the assumed 48-hour lag. Earlier calibration/test
outcomes can enter later match histories after that lag. Model weights remain
frozen after training and residuals after calibration. No final-test outcome is
used to fit weights, calibrate the distribution or choose model parameters.

One canonical player-ID ordering is used per match. Predicted Total Games is
shifted by calibration-only empirical residuals, rounded to integers and floored
at zero. This is a deliberately simple empirical distribution, not a tennis
score-generating model; it may assign mass to impossible scores. No offered-line
probabilities are computed.

## Recorded result

45,331 training, 11,102 calibration, 12,312 final-test matches; 984 boundary-purged.
Calibration starts August 15 and final test September 29, 2026 (UTC).

CRPS (lower is better): **2.805**, versus **3.028** for the training-only empirical
Total Games climatology. Nominal 50% / 80% / 90% interval coverage is 55.44% /
83.98% / 92.52%; average widths are 6.61 / 13.43 / 16.69 games. Integer boundary
ties can increase measured coverage. These results describe one historical
mixed-competition sample, not betting accuracy or validated public confidence.

## Release gates remain closed

Observed result-availability receipts; licensed verified future opponent,
surface, tour and scheduled format; identity crosswalks; prospective and
competition-specific distribution validation; valid tennis score support;
immutable actual standard offers and forecasts; independent held-out
Over/Under/Push validation; and exact settlement/retirement rules are still
required. No research metric automatically authorizes activation.

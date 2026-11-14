# Tennis activation readiness (2026-11-14)

Status: offline research only; NOT a deployed pick feed.

## Verified in this investigation
- Existing builder, features, seven XGBoost target trainers and CLI scanner exist.
- No trained tennis weights or training dataset are present in this checkout. Saved historical metrics do not establish performance against offered lines.
- Configured Sackmann ATP raw annual 2024/2025/2026 and fallback activity/current URLs returned HTTP 404 during this check. ATP/WTA repository page checks also failed with 404. This is an observed source-access failure, not proof why the source is unavailable.
- Current executor has pandas/sklearn but lacks xgboost and requests. Do not use the interactive scanner as a smoke test: it can fetch paid partner quotes.
- Opponent feature joins used player + tournament start date. A player competes multiple times in a tournament; this can multiply rows and attach the wrong match context. The isolated repair preserves match_num and joins reciprocal identities using tour, tournament, match number, date and both players. Six offline regression tests pass.

## Required before training or launch
1. Restore an authorized, maintained ATP/WTA historical source with license and source/freshness receipts. Rebuild raw data; older raw files lack match_num and should fail closed.
2. Repair temporal validation and feature generation. Current training splits rows, not exclusive dates/tournaments, and feature windows use tournament start dates rather than actual ordered match times. Do not call the existing validation prospective.
3. Remove misleading betting-confidence labels based on direction versus the training mean. Evaluate independent chronological holdout projection errors against baselines. Real offered-line probability calibration requires real pre-match quotes and held-out outcomes.
4. Fix inference to use verified upcoming opponent, surface, format and availability, not opponent rank 50 and the player's last-match surface. Missing identity/context should withhold a prediction.
5. Create a dedicated noninteractive, zero-paid-call offline test/training command with minimal pinned dependencies and artifact manifests. Keep model artifacts and research output separate from NBA/NFL.
6. Establish authorized quote capture (standard lines), immutable pre-match predictions, final result matching and push/retirement handling. Verify automation and live phone display before enabling a tennis tab.

No tennis schedule, provider spend, trained weights, public forecasts or NBA/NFL changes were made.

## November 14: lawful fresh score-only research path

[Valuebetennis's season exports](https://www.valuebetennis.com/en/donnees.htm)
are explicitly CC BY 4.0, including commercial reuse with attribution. The local
2026 file contains 79,079 matches through November 14 06:05 UTC. The strict
importer accepts 69,901 complete conventional scores and rejects 9,178 unsupported
or incomplete records. It does not invent serve stats, ranking, score orientation,
or result availability timestamps. Player IDs are namespaced to prevent accidental
joins to the older provider. Source dates denote match starts, not completion.

A separate runnable **offline score-only research model** now exists:

```sh
OMP_NUM_THREADS=2 python -m src.sports.tennis.score_research \
  --csv /path/to/legitimately-obtained-season.csv \
  --output-dir /path/to/research-models \
  --as-of 2026-11-14T19:30:00Z
```

This command imports local data only, trains three score-total regressors, and
saves local research weights plus a machine-readable evaluation. It never calls
PrizePicks, publishes predictions, or changes the live NBA/NFL feeds. Never call
its outputs hit probabilities. Closing/opening odds are deliberately excluded.

The recorded chronological holdout has 60,904 training matches and 8,246 test
matches. Mean absolute errors (model vs training-mean baseline) are 4.189 vs 4.510
games, 0.331 vs 0.352 sets, and 0.344 vs 0.360 tiebreaks. These are exploratory
regression metrics, **not betting hit rates**. This experiment includes multiple
competition levels and only one temporal holdout; prospective, competition-level
validation remains necessary. See `tennis_score_evaluation_2026-11-14.json`.

The research path assumes a 48-hour result-availability lag from match start;
this is not verified publication provenance. It has no future fixture feed,
calibrated per-offered-line Over/Under/Push distribution, or live integration.
The original Sackmann feature path separately uses a conservative 21-day lag
because its dates are tournament starts. Its trainer rejects unversioned legacy
features and splits whole dates with an embargo. These safeguards do not restore
the old scanner's guessed opponent/surface context; it must not be activated.

**Release blockers:** a verified future-fixture/context feed, observed result
availability, training/inference parity for those fixtures, calibrated held-out
line probabilities, freshness/recovery automation, and live mobile QA. No tennis
production activation is claimed by this change.

## Fixture inference integration boundary

`src.sports.tennis.fixture_inference.predict_fixture` now shares the training
feature builder. It requires a locally supplied upcoming fixture with an explicit
UTC/timezone timestamp, scheduled status, observed timestamp, source URL, tour,
surface and two exact namespaced player IDs. It refuses stale/future observations,
unknown or insufficient player history, future historical results and incompatible
or future-trained model artifacts. It never substitutes a previous opponent,
surface or surname match. Outputs are explicitly research-only projections with
no probabilities, no provider calls and no publishing side effects.

This is **not an automated fixture feed**. On November 14 the official TheSportsDB
free schedule endpoints returned `events:null` for November 14 and 15 tennis.
Its limited free development endpoints do not establish complete fixture coverage.
Valuebetennis's explicit open-data licence covers season result CSVs, not a fixture
API; no future-fixture API permission was found. A permitted fixture/context export
or authorized provider access remains required. Cross-provider IDs require an
explicit validated mapping. The score model also lacks verified match-format and
competition-level context; this remains another reason not to publish it live.

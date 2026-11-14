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

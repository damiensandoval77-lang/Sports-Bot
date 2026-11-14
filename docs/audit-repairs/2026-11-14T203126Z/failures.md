## Run 43637805238 / job 132578395704

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43637805238

```text
2026-11-14T20:30:30.7937810Z test_blocked_feed_preserves_old (test_short_history_archive.ArchiveTests.test_blocked_feed_preserves_old) ... ok
2026-11-14T20:30:30.7942377Z test_invalid_and_ineligible_fail_closed (test_short_history_archive.ArchiveTests.test_invalid_and_ineligible_fail_closed) ... ok
2026-11-14T20:30:30.7949399Z test_duplicate_game_date_fails_closed (test_short_history_candidate.ShortHistoryTests.test_duplicate_game_date_fails_closed) ... ok
2026-11-14T20:30:30.7950814Z test_missing_actual_opponent_context_is_not_filled (test_short_history_candidate.ShortHistoryTests.test_missing_actual_opponent_context_is_not_filled) ... ok
2026-11-14T20:30:30.7966075Z test_artifact_load_real_and_tampering (test_short_history_direct_capture.Tests.test_artifact_load_real_and_tampering) ... ERROR
2026-11-14T20:30:30.8022613Z test_error_clears_previous_output (test_short_history_inference.ArtifactAndPublicationTests.test_error_clears_previous_output) ... ok
2026-11-14T20:30:30.8023973Z test_stale_and_future_history_fail (test_short_history_inference.ArtifactAndPublicationTests.test_stale_and_future_history_fail) ... ok
2026-11-14T20:30:30.8033920Z test_failed_market_gate_cannot_be_overridden_by_flag (test_short_history_inference.InferenceTests.test_failed_market_gate_cannot_be_overridden_by_flag) ... ok
2026-11-14T20:30:30.8070664Z test_missing_or_posttip_archive_rejected (test_short_history_offered_line_audit.AuditTests.test_missing_or_posttip_archive_rejected) ... ok
2026-11-14T20:30:30.9254537Z test_runs_after_primary_even_on_failure (test_short_history_workflow.IsolatedResearchWorkflowTests.test_runs_after_primary_even_on_failure) ... ok
2026-11-14T20:30:30.9415543Z test_source_failure_clears_and_only_separate_outputs_are_published (test_short_history_workflow.IsolatedResearchWorkflowTests.test_source_failure_clears_and_only_separate_outputs_are_published) ... ok
2026-11-14T20:30:30.9417426Z ERROR: test_artifact_load_real_and_tampering (test_short_history_direct_capture.Tests.test_artifact_load_real_and_tampering)
2026-11-14T20:30:30.9427609Z     if manifest['model']!=MODEL or manifest['spec_sha256']!=digest(SPEC.read_bytes()) or manifest['code_sha256']!=code_hashes() or manifest['versions']!=versions():raise ValueError('FROZEN_BUNDLE_PROVENANCE_MISMATCH')
2026-11-14T20:30:30.9429388Z ValueError: FROZEN_BUNDLE_PROVENANCE_MISMATCH
2026-11-14T20:30:30.9430461Z FAILED (errors=1)
2026-11-14T20:30:31.0762509Z ##[error]Process completed with exit code 1.
```

## Run 43637069247 / job 132576088341

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43637069247

```text
2026-11-14T20:21:42.3685116Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T20:22:08.1107832Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T20:21:42.472799+00:00", "error": null}
2026-11-14T20:22:08.1765696Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T20:22:08.2210172Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:22:08.2255919Z ##[error]Process completed with exit code 2.
2026-11-14T20:22:08.2300254Z ##[group]Run set -euo pipefail
2026-11-14T20:22:08.2300593Z [36;1mset -euo pipefail[0m
2026-11-14T20:22:08.2310689Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T20:22:09.2228428Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:22:10.8307652Z ##[group]Run set -euo pipefail
2026-11-14T20:22:10.8307882Z [36;1mset -euo pipefail[0m
2026-11-14T20:22:10.8311095Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T20:22:10.8312601Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T20:22:10.8312867Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T20:22:10.8313325Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T20:22:10.8313563Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T20:22:10.8314872Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T20:22:10.8315120Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T20:22:10.8316389Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T20:22:10.8318102Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T20:22:10.8318703Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T20:22:12.2715592Z Skipping nba-prizepicks-full-slate.yml: active, successful cooldown, or failure backoff (paid calls hard-capped)
2026-11-14T20:22:12.2757912Z ##[group]Run set -euo pipefail
2026-11-14T20:22:12.2758262Z [36;1mset -euo pipefail[0m
2026-11-14T20:22:12.2759084Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T20:22:12.2770429Z [36;1m  echo "### Failing required components"[0m
2026-11-14T20:22:12.2773407Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T20:22:12.7075416Z   if-no-files-found: error
2026-11-14T20:22:13.1466870Z (node:2339) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:22:13.8147995Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T20:22:13.8266404Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T20:22:13.8268466Z ##[error]Process completed with exit code 1.
```

## Run 43636039095 / job 132572941898

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43636039095

```text
2026-11-14T20:10:26.9440837Z ##[group]Run set -euo pipefail
2026-11-14T20:10:26.9441302Z [36;1mset -euo pipefail[0m
2026-11-14T20:10:26.9445160Z [36;1m  # cannot remain blocked by an earlier cached audit snapshot.[0m
2026-11-14T20:10:26.9445612Z [36;1m  for module in audit_ai_forecast_coverage production_readiness unified_dames_readiness; do[0m
2026-11-14T20:10:26.9448844Z [36;1m  git add docs/ai_forecast_coverage_audit.json docs/production_readiness.json docs/dames-picks/unified_readiness.json docs/dames-picks/app_release_gate.json[0m
2026-11-14T20:10:26.9450843Z [36;1mecho "::error::Could not publish merged app release verification"[0m
2026-11-14T20:10:30.3398276Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T20:10:30.4523173Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:10:30.4784978Z DAMES_PICKS_RELEASE_GATE {"checked_at": "2026-11-14T20:10:30.477606+00:00", "status": "DEGRADED", "checks_passing": false, "release_certified": false, "healthy_streak_started_at": null, "healthy_streak_hours": 0.0, "required_consecutive_hours": 72, "blocking_checks": ["unified_artifacts", "nba_production", "nba_capture"], "checks": {"unified_artifacts": {"state": "DEGRADED", "issues": ["UNIFIED_APP_ARTIFACTS_NOT_READY", "NBA_OR_NFL_ARTIFACTS_NOT_READY"]}, "public_unified_browser": {"state": "READY", "issues": []}, "nba_production": {"state": "DEGRADED", "issues": ["NBA_PRODUCTION_NOT_READY", "NBA_FAILED_CURRENT_PRIMARY_MODEL_COVERAGE"]}, "nba_capture": {"state": "DEGRADED", "issues": ["PRIMARY_STANDARD_COVERAGE_INCOMPLETE"]}, "nba_grading": {"state": "READY", "issues": []}, "published_pick_settlement": {"state": "READY", "issues": []}, "nfl_grading": {"state": "READY", "issues": []}}, "scope": "UNIFIED_DAMES_PICKS_NBA_NFL_RELEASE_GATE", "note": "72h sustained clean artifacts and observed public browser, pretip captures, frozen standard-only grading and current source gates; this does not prove predictive accuracy or zero downtime."}
2026-11-14T20:10:32.6281794Z ##[error]Process completed with exit code 2.
```

## Run 43635757317 / job 132572071864

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635757317

```text
2026-11-14T20:07:21.1409328Z test_missing_eighth_game_match_is_not_ready (test_end_to_end_readiness.ReadinessTests.test_missing_eighth_game_match_is_not_ready) ... ok
2026-11-14T20:07:21.1410361Z test_missing_schedule_fails_closed (test_end_to_end_readiness.ReadinessTests.test_missing_schedule_fails_closed) ... ok
2026-11-14T20:07:21.1413633Z test_stale_data_and_missing_grades_fail (test_end_to_end_readiness.ReadinessTests.test_stale_data_and_missing_grades_fail) ... ok
2026-11-14T20:07:21.1907865Z   "status": "DEGRADED",
2026-11-14T20:07:21.1912677Z   "failures": [
2026-11-14T20:07:21.1954356Z ##[error]Process completed with exit code 1.
2026-11-14T20:07:21.2037312Z   if-no-files-found: error
2026-11-14T20:07:21.6131506Z (node:2393) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
```

## Run 43635695332 / job 132571881435

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635695332

```text
2026-11-14T20:06:36.2484271Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T20:07:01.8279148Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T20:06:36.397108+00:00", "error": null}
2026-11-14T20:07:01.9298969Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T20:07:01.9955698Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T20:07:02.0027225Z ##[error]Process completed with exit code 2.
2026-11-14T20:07:02.0093064Z ##[group]Run set -euo pipefail
2026-11-14T20:07:02.0093510Z [36;1mset -euo pipefail[0m
2026-11-14T20:07:02.0105324Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T20:07:02.5106897Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T20:07:04.6511815Z ##[group]Run set -euo pipefail
2026-11-14T20:07:04.6512181Z [36;1mset -euo pipefail[0m
2026-11-14T20:07:04.6518303Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T20:07:04.6520998Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T20:07:04.6521494Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T20:07:04.6522644Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T20:07:04.6523078Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T20:07:04.6525104Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T20:07:04.6525554Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T20:07:04.6527847Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T20:07:04.6530895Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T20:07:04.6531975Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T20:07:04.6978212Z ##[group]Run set -euo pipefail
2026-11-14T20:07:04.6978563Z [36;1mset -euo pipefail[0m
2026-11-14T20:07:04.6979506Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T20:07:04.6991532Z [36;1m  echo "### Failing required components"[0m
2026-11-14T20:07:04.6995161Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T20:07:05.1543003Z   if-no-files-found: error
2026-11-14T20:07:05.7311031Z (node:2961) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:07:06.4876890Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T20:07:06.5029476Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T20:07:06.5031853Z ##[error]Process completed with exit code 1.
```

## Run 43635695300 / job 132571881320

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635695300

```text
2026-11-14T20:06:36.5098600Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T20:06:37.8541561Z {"checked_at": "2026-11-14T20:06:36.559667+00:00", "recoveries": [{"workflow": "nba-new-ai-all-markets.yml", "status": "SKIPPED", "reason": "ACTIVE_RECENT_SUCCESS_OR_FAILURE_BACKOFF"}], "status": "COMPLETE", "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}
2026-11-14T20:06:39.2973259Z (node:2142) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:06:39.8097427Z [36;1m  echo "- **FAIL** Heartbeat report missing; inspect failed workflow and artifact." >> "$GITHUB_STEP_SUMMARY"[0m
2026-11-14T20:06:39.8244884Z ##[group]Run set -euo pipefail
2026-11-14T20:06:39.8245387Z [36;1mset -euo pipefail[0m
2026-11-14T20:06:39.8248213Z [36;1mgh label create pipeline-alert --color B60205 --description "Dame's Picks pipeline failure" 2>/dev/null || true[0m
2026-11-14T20:06:39.8249957Z [36;1m  title="[pipeline] $stage failing"[0m
2026-11-14T20:06:39.8251191Z [36;1m  if [ "$status" = FAIL ] && [ -z "$issue" ]; then[0m
2026-11-14T20:06:40.2320872Z ##[error]Process completed with exit code 1.
```

## Run 43635404649 / job 132570995920

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635404649

```text
2026-11-14T20:03:28.9709722Z ##[group]Run python -m iphone_bot.audit_primary_model_missing
2026-11-14T20:03:28.9710267Z [36;1mpython -m iphone_bot.audit_primary_model_missing[0m
2026-11-14T20:03:29.4635459Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:03:29.416834+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 2, "unique_provider_player_stat_markets": 38, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 76, "standard_source_quotes": 76, "standard_unique_markets": 76, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 15, "missing_primary_with_separate_research_receipt": 15, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 40, "frozen_ai_only": 108, "frozen_line_backed": 61, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 61, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 59, "standard_source_quotes": 59, "standard_unique_markets": 59, "standard_markets_without_frozen_model": 3, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 3, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 3, "unique_provider_player_stat_markets": 41, "frozen_ai_only": 100, "frozen_line_backed": 56, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 56, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 0, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 0, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 36, "frozen_ai_only": 96, "frozen_line_backed": 51, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 51, "issues": []}], "issues": ["Denver Nuggets @ New Orleans Pelicans: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Dallas Mavericks @ Cleveland Cavaliers: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Brooklyn Nets @ Memphis Grizzlies: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Chicago Bulls @ Minnesota Timberwolves: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"], "note": "Provider quotes, AI-only forecasts, line-backed frozen predictions and final grades are separate. Missing records never fabricated.", "summary": {"schedule_games": 5, "games_with_saved_source_quotes": 5, "games_with_frozen_ai": 5, "games_with_line_backed_models": 5, "total_quotes": 311, "total_standard_source_quotes": 311, "total_standard_markets_without_frozen_model": 28, "total_price_moves_from_original_frozen_line": 0, "total_player_stat_markets_never_primary_frozen": 28, "total_missing_primary_with_separate_research_receipt": 23, "total_missing_primary_without_any_ai_receipt": 5, "total_ai_only": 504, "total_line_backed": 283, "total_line_backed_graded": 0, "total_ai_only_graded": 0}, "current_upcoming_coverage": {"status": "INCOMPLETE", "checked_at": "2026-11-14T20:03:29.416834+00:00", "source_generated_at": "2026-11-14T19:12:37.729953+00:00", "verified_current_offers": 174, "matched_primary_offers": 159, "missing_primary_offers": 15, "games": [{"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 37, "matched_primary_offers": 28, "missing_primary_offers": 9, "missing": [{"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PRA", "line": 15.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "REB", "line": 2.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PTS", "line": 10.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "REB", "line": 4.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PTS", "line": 6.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PRA", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PTS", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PRA", "line": 18.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "AST", "line": 3.5}]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 36, "matched_primary_offers": 34, "missing_primary_offers": 2, "missing": [{"player": "Nic Claxton", "team": "CHI", "stat": "PTS", "line": 7.5}, {"player": "Nic Claxton", "team": "CHI", "stat": "PRA", "line": 15.5}]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "verified_current_offers": 35, "matched_primary_offers": 35, "missing_primary_offers": 0, "missing": []}, {"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "verified_current_offers": 34, "matched_primary_offers": 30, "missing_primary_offers": 4, "missing": [{"player": "Cameron Johnson", "team": "DEN", "stat": "PTS", "line": 12.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "PRA", "line": 18.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "REB", "line": 3.5}, {"player": "Spencer Jones", "team": "DEN", "stat": "REB", "line": 2.5}]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 32, "matched_primary_offers": 32, "missing_primary_offers": 0, "missing": []}], "issues": [], "scope": "CURRENT_UPCOMING_STANDARD_OFFERS_ONLY", "research_and_provisional_count_as_primary": false}}
2026-11-14T20:03:29.4708081Z ##[error]Process completed with exit code 1.
2026-11-14T20:03:29.4781774Z ##[group]Run set -euo pipefail
2026-11-14T20:03:29.4782108Z [36;1mset -euo pipefail[0m
2026-11-14T20:03:29.4785111Z [36;1m  python -m iphone_bot.audit_primary_model_missing[0m
2026-11-14T20:03:29.4786568Z [36;1m  git add docs/tonight_capture_gradeability.json docs/primary_model_missing_diagnostics.json[0m
2026-11-14T20:03:29.4788710Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T20:03:31.8650227Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:03:31.821821+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 2, "unique_provider_player_stat_markets": 38, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 76, "standard_source_quotes": 76, "standard_unique_markets": 76, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 15, "missing_primary_with_separate_research_receipt": 15, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 40, "frozen_ai_only": 108, "frozen_line_backed": 61, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 61, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 59, "standard_source_quotes": 59, "standard_unique_markets": 59, "standard_markets_without_frozen_model": 3, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 3, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 3, "unique_provider_player_stat_markets": 41, "frozen_ai_only": 100, "frozen_line_backed": 56, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 56, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 0, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 0, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 36, "frozen_ai_only": 96, "frozen_line_backed": 51, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 51, "issues": []}], "issues": ["Denver Nuggets @ New Orleans Pelicans: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Dallas Mavericks @ Cleveland Cavaliers: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Brooklyn Nets @ Memphis Grizzlies: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Chicago Bulls @ Minnesota Timberwolves: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"], "note": "Provider quotes, AI-only forecasts, line-backed frozen predictions and final grades are separate. Missing records never fabricated.", "summary": {"schedule_games": 5, "games_with_saved_source_quotes": 5, "games_with_frozen_ai": 5, "games_with_line_backed_models": 5, "total_quotes": 311, "total_standard_source_quotes": 311, "total_standard_markets_without_frozen_model": 28, "total_price_moves_from_original_frozen_line": 0, "total_player_stat_markets_never_primary_frozen": 28, "total_missing_primary_with_separate_research_receipt": 23, "total_missing_primary_without_any_ai_receipt": 5, "total_ai_only": 504, "total_line_backed": 283, "total_line_backed_graded": 0, "total_ai_only_graded": 0}, "current_upcoming_coverage": {"status": "INCOMPLETE", "checked_at": "2026-11-14T20:03:31.821821+00:00", "source_generated_at": "2026-11-14T19:12:37.729953+00:00", "verified_current_offers": 174, "matched_primary_offers": 159, "missing_primary_offers": 15, "games": [{"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 37, "matched_primary_offers": 28, "missing_primary_offers": 9, "missing": [{"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PRA", "line": 15.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "REB", "line": 2.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PTS", "line": 10.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "REB", "line": 4.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PTS", "line": 6.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PRA", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PTS", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PRA", "line": 18.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "AST", "line": 3.5}]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 36, "matched_primary_offers": 34, "missing_primary_offers": 2, "missing": [{"player": "Nic Claxton", "team": "CHI", "stat": "PTS", "line": 7.5}, {"player": "Nic Claxton", "team": "CHI", "stat": "PRA", "line": 15.5}]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "verified_current_offers": 35, "matched_primary_offers": 35, "missing_primary_offers": 0, "missing": []}, {"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "verified_current_offers": 34, "matched_primary_offers": 30, "missing_primary_offers": 4, "missing": [{"player": "Cameron Johnson", "team": "DEN", "stat": "PTS", "line": 12.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "PRA", "line": 18.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "REB", "line": 3.5}, {"player": "Spencer Jones", "team": "DEN", "stat": "REB", "line": 2.5}]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 32, "matched_primary_offers": 32, "missing_primary_offers": 0, "missing": []}], "issues": [], "scope": "CURRENT_UPCOMING_STANDARD_OFFERS_ONLY", "research_and_provisional_count_as_primary": false}}
2026-11-14T20:03:33.0801419Z ##[error]Process completed with exit code 1.
2026-11-14T20:03:33.0839118Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T20:03:33.0840273Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T20:03:33.0975799Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T20:03:33.0978020Z ##[error]Process completed with exit code 1.
```

## Run 43635297998 / job 132570664719

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635297998

```text
2026-11-14T20:02:21.8496973Z Unreadable deployed feed lagged_matchup_live_all_markets.json HTTP Error 503: Service Unavailable
2026-11-14T20:02:22.5743508Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T20:02:25.2427226Z {"checked_at": "2026-11-14T20:02:22.635104+00:00", "recoveries": [{"workflow": "nba-new-ai-all-markets.yml", "status": "DISPATCHED"}], "status": "COMPLETE", "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}
2026-11-14T20:02:26.8073022Z (node:2387) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:02:27.5718600Z [36;1m  echo "- **FAIL** Heartbeat report missing; inspect failed workflow and artifact." >> "$GITHUB_STEP_SUMMARY"[0m
2026-11-14T20:02:27.5895622Z ##[group]Run set -euo pipefail
2026-11-14T20:02:27.5896289Z [36;1mset -euo pipefail[0m
2026-11-14T20:02:27.5899946Z [36;1mgh label create pipeline-alert --color B60205 --description "Dame's Picks pipeline failure" 2>/dev/null || true[0m
2026-11-14T20:02:27.5901660Z [36;1m  title="[pipeline] $stage failing"[0m
2026-11-14T20:02:27.5903223Z [36;1m  if [ "$status" = FAIL ] && [ -z "$issue" ]; then[0m
2026-11-14T20:02:27.9982144Z ##[error]Process completed with exit code 1.
```

## Run 43635297956 / job 132570664640

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635297956

```text
2026-11-14T20:02:20.1640922Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T20:02:45.8842701Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T20:02:20.431102+00:00", "error": null}
2026-11-14T20:02:45.9590809Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T20:02:46.0169748Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T20:02:46.0231685Z ##[error]Process completed with exit code 2.
2026-11-14T20:02:46.0290201Z ##[group]Run set -euo pipefail
2026-11-14T20:02:46.0290553Z [36;1mset -euo pipefail[0m
2026-11-14T20:02:46.0300082Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T20:02:47.6385113Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T20:02:49.3622310Z ##[group]Run set -euo pipefail
2026-11-14T20:02:49.3622648Z [36;1mset -euo pipefail[0m
2026-11-14T20:02:49.3627134Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T20:02:49.3629237Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T20:02:49.3629607Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T20:02:49.3630248Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T20:02:49.3630571Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T20:02:49.3632383Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T20:02:49.3632731Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T20:02:49.3634497Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T20:02:49.3636872Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T20:02:49.3637707Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T20:02:49.4020308Z ##[group]Run set -euo pipefail
2026-11-14T20:02:49.4020619Z [36;1mset -euo pipefail[0m
2026-11-14T20:02:49.4021479Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T20:02:49.4030939Z [36;1m  echo "### Failing required components"[0m
2026-11-14T20:02:49.4033842Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T20:02:49.8788253Z   if-no-files-found: error
2026-11-14T20:02:50.4275241Z (node:2275) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:02:51.2218772Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T20:02:51.2356048Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T20:02:51.2357913Z ##[error]Process completed with exit code 1.
```

## Run 43635265762 / job 132570565450

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635265762

```text
2026-11-14T20:02:21.6252592Z PUBLIC_DIAGNOSTICS_AUDIT {"checked_at": "2026-11-14T20:02:21.559536+00:00", "public": {"release": "dp-live-kickoff-cache-safe-20261114-r42", "diagnosticDisplay": "none", "diagnosticVisible": false, "statusVisible": false, "verifyVisible": false, "cardsVisible": true, "cardsCount": 182, "healthTextVisible": false}, "diagnostics": {"diagnosticDisplay": "block", "summaryVisible": true, "open": false, "verifyInitiallyVisible": false, "verifyAfterOpen": true, "statusAfterOpen": true, "releaseVerified": false}, "errors": [], "status": "BLOCKED"}
2026-11-14T20:02:21.6490802Z ##[error]Process completed with exit code 1.
2026-11-14T20:02:22.0391612Z (node:2987) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
```

## Run 43635265725 / job 132570565385

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635265725

```text
2026-11-14T20:01:58.6813680Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:01:58.6875899Z ##[error]Process completed with exit code 2.
2026-11-14T20:01:58.6931733Z ##[group]Run set -euo pipefail
2026-11-14T20:01:58.6932020Z [36;1mset -euo pipefail[0m
2026-11-14T20:02:00.0433582Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:02:01.2522418Z ##[error]Process completed with exit code 2.
2026-11-14T20:02:01.2555135Z ##[group]Run echo "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"
2026-11-14T20:02:01.2555806Z [36;1mecho "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"[0m
2026-11-14T20:02:01.2669530Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T20:02:01.2670967Z ##[error]Process completed with exit code 1.
```

## Run 43635106250 / job 132570093804

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635106250

```text
2026-11-14T20:00:22.1319031Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T20:00:47.5365241Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T20:00:22.299606+00:00", "error": null}
2026-11-14T20:00:47.6305184Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T20:00:47.6936482Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T20:00:47.7001127Z ##[error]Process completed with exit code 2.
2026-11-14T20:00:47.7055320Z ##[group]Run set -euo pipefail
2026-11-14T20:00:47.7055664Z [36;1mset -euo pipefail[0m
2026-11-14T20:00:47.7067276Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T20:00:49.9188601Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T20:00:51.6964464Z ##[group]Run set -euo pipefail
2026-11-14T20:00:51.6964825Z [36;1mset -euo pipefail[0m
2026-11-14T20:00:51.6970670Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T20:00:51.6973295Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T20:00:51.6973777Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T20:00:51.6974590Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T20:00:51.6974995Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T20:00:51.6977001Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T20:00:51.6977466Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T20:00:51.6979972Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T20:00:51.7003129Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T20:00:51.7004204Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T20:00:51.7443683Z ##[group]Run set -euo pipefail
2026-11-14T20:00:51.7444046Z [36;1mset -euo pipefail[0m
2026-11-14T20:00:51.7444938Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T20:00:51.7456722Z [36;1m  echo "### Failing required components"[0m
2026-11-14T20:00:51.7460240Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T20:00:52.3077843Z   if-no-files-found: error
2026-11-14T20:00:52.7597960Z (node:2494) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:00:53.1787997Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T20:00:53.1945869Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T20:00:53.1947839Z ##[error]Process completed with exit code 1.
```

## Run 43635076066 / job 132570008322

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635076066

```text
2026-11-14T20:06:25.6223071Z   "status": "FAIL",
2026-11-14T20:06:39.1496338Z       "status": "FAIL",
2026-11-14T20:06:39.1502110Z       "status": "FAIL",
2026-11-14T20:06:39.1518076Z       "status": "FAIL",
2026-11-14T20:06:39.1534741Z         "error": "Feed request timed out",
2026-11-14T20:06:39.1587947Z       "status": "FAIL",
2026-11-14T20:06:39.1595011Z       "name": "missing_games_disclosed",
2026-11-14T20:06:39.1596526Z   "overall": "FAIL"
2026-11-14T20:06:39.7678523Z (node:3341) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:06:40.4020860Z ##[error]Process completed with exit code 1.
```

## Run 43635076066 / job 132570008482

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43635076066

```text
2026-11-14T20:06:59.8731608Z   "status": "FAIL",
2026-11-14T20:07:17.8575734Z       "status": "FAIL",
2026-11-14T20:07:17.8577813Z       "status": "FAIL",
2026-11-14T20:07:17.8692818Z       "status": "FAIL",
2026-11-14T20:07:17.8702365Z         "error": "Feed request timed out",
2026-11-14T20:07:17.8742299Z       "status": "FAIL",
2026-11-14T20:07:17.8747852Z       "name": "missing_games_disclosed",
2026-11-14T20:07:17.8749098Z   "overall": "FAIL"
2026-11-14T20:07:18.5911461Z (node:5104) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:07:19.0157368Z ##[error]Process completed with exit code 1.
```

## Run 43634968382 / job 132569663738

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634968382

```text
2026-11-14T19:58:47.8959750Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T19:58:49.2048509Z {"checked_at": "2026-11-14T19:58:47.955558+00:00", "recoveries": [{"workflow": "nba-new-ai-all-markets.yml", "status": "SKIPPED", "reason": "ACTIVE_RECENT_SUCCESS_OR_FAILURE_BACKOFF"}], "status": "COMPLETE", "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}
2026-11-14T19:58:50.6291380Z (node:2368) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:58:51.3557182Z [36;1m  echo "- **FAIL** Heartbeat report missing; inspect failed workflow and artifact." >> "$GITHUB_STEP_SUMMARY"[0m
2026-11-14T19:58:51.3752294Z ##[group]Run set -euo pipefail
2026-11-14T19:58:51.3752628Z [36;1mset -euo pipefail[0m
2026-11-14T19:58:51.3756226Z [36;1mgh label create pipeline-alert --color B60205 --description "Dame's Picks pipeline failure" 2>/dev/null || true[0m
2026-11-14T19:58:51.3757978Z [36;1m  title="[pipeline] $stage failing"[0m
2026-11-14T19:58:51.3759873Z [36;1m  if [ "$status" = FAIL ] && [ -z "$issue" ]; then[0m
2026-11-14T19:58:51.7875261Z ##[error]Process completed with exit code 1.
```

## Run 43634653018 / job 132568691460

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634653018

```text
2026-11-14T19:55:06.0159656Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T19:55:06.0225586Z ##[error]Process completed with exit code 2.
2026-11-14T19:55:06.0294758Z ##[group]Run set -euo pipefail
2026-11-14T19:55:06.0295489Z [36;1mset -euo pipefail[0m
2026-11-14T19:55:07.4840450Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T19:55:10.4510120Z ##[error]Process completed with exit code 2.
2026-11-14T19:55:10.4562802Z ##[group]Run echo "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"
2026-11-14T19:55:10.4563615Z [36;1mecho "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"[0m
2026-11-14T19:55:10.4669248Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T19:55:10.4671288Z ##[error]Process completed with exit code 1.
```

## Run 43634653009 / job 132568690925

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634653009

```text
2026-11-14T19:55:05.1063343Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T19:55:30.7229038Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T19:55:05.209898+00:00", "error": null}
2026-11-14T19:55:30.8251299Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T19:55:30.8744848Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:55:30.8790714Z ##[error]Process completed with exit code 2.
2026-11-14T19:55:30.8831544Z ##[group]Run set -euo pipefail
2026-11-14T19:55:30.8831813Z [36;1mset -euo pipefail[0m
2026-11-14T19:55:30.8838435Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T19:55:32.1590010Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:55:33.5368534Z ##[group]Run set -euo pipefail
2026-11-14T19:55:33.5368755Z [36;1mset -euo pipefail[0m
2026-11-14T19:55:33.5371777Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T19:55:33.5373205Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T19:55:33.5373460Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T19:55:33.5373897Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T19:55:33.5374264Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T19:55:33.5375345Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T19:55:33.5375578Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T19:55:33.5376775Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T19:55:33.5378410Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T19:55:33.5378988Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T19:55:33.5678719Z ##[group]Run set -euo pipefail
2026-11-14T19:55:33.5678923Z [36;1mset -euo pipefail[0m
2026-11-14T19:55:33.5679459Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T19:55:33.5685782Z [36;1m  echo "### Failing required components"[0m
2026-11-14T19:55:33.5687505Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T19:55:34.1956560Z   if-no-files-found: error
2026-11-14T19:55:34.6145338Z (node:2262) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:55:35.1703160Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T19:55:35.1824667Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T19:55:35.1835889Z ##[error]Process completed with exit code 1.
```

## Run 43634627353 / job 132568609313

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634627353

```text
2026-11-14T19:54:46.6882190Z ##[group]Run python -m iphone_bot.audit_primary_model_missing
2026-11-14T19:54:46.6882631Z [36;1mpython -m iphone_bot.audit_primary_model_missing[0m
2026-11-14T19:54:47.0394198Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T19:54:47.000971+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 2, "unique_provider_player_stat_markets": 38, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 76, "standard_source_quotes": 76, "standard_unique_markets": 76, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 15, "missing_primary_with_separate_research_receipt": 15, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 40, "frozen_ai_only": 108, "frozen_line_backed": 61, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 61, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 59, "standard_source_quotes": 59, "standard_unique_markets": 59, "standard_markets_without_frozen_model": 3, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 3, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 3, "unique_provider_player_stat_markets": 41, "frozen_ai_only": 100, "frozen_line_backed": 56, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 56, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 0, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 0, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 36, "frozen_ai_only": 96, "frozen_line_backed": 51, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 51, "issues": []}], "issues": ["Denver Nuggets @ New Orleans Pelicans: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Dallas Mavericks @ Cleveland Cavaliers: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Brooklyn Nets @ Memphis Grizzlies: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Chicago Bulls @ Minnesota Timberwolves: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"], "note": "Provider quotes, AI-only forecasts, line-backed frozen predictions and final grades are separate. Missing records never fabricated.", "summary": {"schedule_games": 5, "games_with_saved_source_quotes": 5, "games_with_frozen_ai": 5, "games_with_line_backed_models": 5, "total_quotes": 311, "total_standard_source_quotes": 311, "total_standard_markets_without_frozen_model": 28, "total_price_moves_from_original_frozen_line": 0, "total_player_stat_markets_never_primary_frozen": 28, "total_missing_primary_with_separate_research_receipt": 23, "total_missing_primary_without_any_ai_receipt": 5, "total_ai_only": 504, "total_line_backed": 283, "total_line_backed_graded": 0, "total_ai_only_graded": 0}, "current_upcoming_coverage": {"status": "INCOMPLETE", "checked_at": "2026-11-14T19:54:47.000971+00:00", "source_generated_at": "2026-11-14T19:12:37.729953+00:00", "verified_current_offers": 174, "matched_primary_offers": 159, "missing_primary_offers": 15, "games": [{"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 37, "matched_primary_offers": 28, "missing_primary_offers": 9, "missing": [{"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PRA", "line": 15.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "REB", "line": 2.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PTS", "line": 10.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "REB", "line": 4.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PTS", "line": 6.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PRA", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PTS", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PRA", "line": 18.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "AST", "line": 3.5}]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 36, "matched_primary_offers": 34, "missing_primary_offers": 2, "missing": [{"player": "Nic Claxton", "team": "CHI", "stat": "PTS", "line": 7.5}, {"player": "Nic Claxton", "team": "CHI", "stat": "PRA", "line": 15.5}]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "verified_current_offers": 35, "matched_primary_offers": 35, "missing_primary_offers": 0, "missing": []}, {"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "verified_current_offers": 34, "matched_primary_offers": 30, "missing_primary_offers": 4, "missing": [{"player": "Cameron Johnson", "team": "DEN", "stat": "PTS", "line": 12.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "PRA", "line": 18.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "REB", "line": 3.5}, {"player": "Spencer Jones", "team": "DEN", "stat": "REB", "line": 2.5}]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 32, "matched_primary_offers": 32, "missing_primary_offers": 0, "missing": []}], "issues": [], "scope": "CURRENT_UPCOMING_STANDARD_OFFERS_ONLY", "research_and_provisional_count_as_primary": false}}
2026-11-14T19:54:47.0458443Z ##[error]Process completed with exit code 1.
2026-11-14T19:54:47.0509652Z ##[group]Run set -euo pipefail
2026-11-14T19:54:47.0509936Z [36;1mset -euo pipefail[0m
2026-11-14T19:54:47.0512324Z [36;1m  python -m iphone_bot.audit_primary_model_missing[0m
2026-11-14T19:54:47.0513271Z [36;1m  git add docs/tonight_capture_gradeability.json docs/primary_model_missing_diagnostics.json[0m
2026-11-14T19:54:47.0514838Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T19:54:48.5388382Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T19:54:48.502590+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 2, "unique_provider_player_stat_markets": 38, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 76, "standard_source_quotes": 76, "standard_unique_markets": 76, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 15, "missing_primary_with_separate_research_receipt": 15, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 40, "frozen_ai_only": 108, "frozen_line_backed": 61, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 61, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 59, "standard_source_quotes": 59, "standard_unique_markets": 59, "standard_markets_without_frozen_model": 3, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 3, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 3, "unique_provider_player_stat_markets": 41, "frozen_ai_only": 100, "frozen_line_backed": 56, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 56, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 0, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 0, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 36, "frozen_ai_only": 96, "frozen_line_backed": 51, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 51, "issues": []}], "issues": ["Denver Nuggets @ New Orleans Pelicans: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Dallas Mavericks @ Cleveland Cavaliers: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Brooklyn Nets @ Memphis Grizzlies: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Chicago Bulls @ Minnesota Timberwolves: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"], "note": "Provider quotes, AI-only forecasts, line-backed frozen predictions and final grades are separate. Missing records never fabricated.", "summary": {"schedule_games": 5, "games_with_saved_source_quotes": 5, "games_with_frozen_ai": 5, "games_with_line_backed_models": 5, "total_quotes": 311, "total_standard_source_quotes": 311, "total_standard_markets_without_frozen_model": 28, "total_price_moves_from_original_frozen_line": 0, "total_player_stat_markets_never_primary_frozen": 28, "total_missing_primary_with_separate_research_receipt": 23, "total_missing_primary_without_any_ai_receipt": 5, "total_ai_only": 504, "total_line_backed": 283, "total_line_backed_graded": 0, "total_ai_only_graded": 0}, "current_upcoming_coverage": {"status": "INCOMPLETE", "checked_at": "2026-11-14T19:54:48.502590+00:00", "source_generated_at": "2026-11-14T19:12:37.729953+00:00", "verified_current_offers": 174, "matched_primary_offers": 159, "missing_primary_offers": 15, "games": [{"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 37, "matched_primary_offers": 28, "missing_primary_offers": 9, "missing": [{"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PRA", "line": 15.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "REB", "line": 2.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PTS", "line": 10.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "REB", "line": 4.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PTS", "line": 6.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PRA", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PTS", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PRA", "line": 18.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "AST", "line": 3.5}]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 36, "matched_primary_offers": 34, "missing_primary_offers": 2, "missing": [{"player": "Nic Claxton", "team": "CHI", "stat": "PTS", "line": 7.5}, {"player": "Nic Claxton", "team": "CHI", "stat": "PRA", "line": 15.5}]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "verified_current_offers": 35, "matched_primary_offers": 35, "missing_primary_offers": 0, "missing": []}, {"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "verified_current_offers": 34, "matched_primary_offers": 30, "missing_primary_offers": 4, "missing": [{"player": "Cameron Johnson", "team": "DEN", "stat": "PTS", "line": 12.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "PRA", "line": 18.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "REB", "line": 3.5}, {"player": "Spencer Jones", "team": "DEN", "stat": "REB", "line": 2.5}]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 32, "matched_primary_offers": 32, "missing_primary_offers": 0, "missing": []}], "issues": [], "scope": "CURRENT_UPCOMING_STANDARD_OFFERS_ONLY", "research_and_provisional_count_as_primary": false}}
2026-11-14T19:54:52.1210907Z ##[error]Process completed with exit code 1.
2026-11-14T19:54:52.1245270Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T19:54:52.1246122Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T19:54:52.1365035Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T19:54:52.1366593Z ##[error]Process completed with exit code 1.
```

## Run 43634376929 / job 132567836892

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634376929

```text
2026-11-14T19:58:48.3143451Z   "status": "FAIL",
2026-11-14T19:59:08.1618546Z       "status": "FAIL",
2026-11-14T19:59:08.1628652Z         "error": "Feed request timed out",
2026-11-14T19:59:08.1674595Z       "name": "missing_games_disclosed",
2026-11-14T19:59:08.1675883Z   "overall": "FAIL"
2026-11-14T19:59:08.6968021Z (node:5105) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:59:09.1403353Z ##[error]Process completed with exit code 1.
```

## Run 43634376929 / job 132567837052

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634376929

```text
2026-11-14T19:58:18.9082370Z   "status": "FAIL",
2026-11-14T19:58:32.1376439Z       "status": "FAIL",
2026-11-14T19:58:32.1389929Z         "error": "Feed request timed out",
2026-11-14T19:58:32.1451381Z       "name": "missing_games_disclosed",
2026-11-14T19:58:32.1452938Z   "overall": "FAIL"
2026-11-14T19:58:32.6618574Z (node:3313) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:58:33.1444095Z ##[error]Process completed with exit code 1.
```

## Run 43634145676 / job 132567133603

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634145676

```text
2026-11-14T19:49:20.4949294Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T19:49:46.2293602Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T19:49:20.620605+00:00", "error": null}
2026-11-14T19:49:46.3011290Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T19:49:46.3488323Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:49:46.3538313Z ##[error]Process completed with exit code 2.
2026-11-14T19:49:46.3613817Z ##[group]Run set -euo pipefail
2026-11-14T19:49:46.3614336Z [36;1mset -euo pipefail[0m
2026-11-14T19:49:46.3620966Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T19:49:47.4797854Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:49:51.1720790Z ##[group]Run set -euo pipefail
2026-11-14T19:49:51.1721022Z [36;1mset -euo pipefail[0m
2026-11-14T19:49:51.1724278Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T19:49:51.1725747Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T19:49:51.1726014Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T19:49:51.1726468Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T19:49:51.1726705Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T19:49:51.1727816Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T19:49:51.1728061Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T19:49:51.1729295Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T19:49:51.1731004Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T19:49:51.1731593Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T19:49:51.2042185Z ##[group]Run set -euo pipefail
2026-11-14T19:49:51.2042388Z [36;1mset -euo pipefail[0m
2026-11-14T19:49:51.2042908Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T19:49:51.2050643Z [36;1m  echo "### Failing required components"[0m
2026-11-14T19:49:51.2052443Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T19:49:51.7382463Z   if-no-files-found: error
2026-11-14T19:49:52.1401635Z (node:2264) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:49:52.7325793Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T19:49:52.7454107Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T19:49:52.7455364Z ##[error]Process completed with exit code 1.
```

## Run 43634141640 / job 132567119812

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634141640

```text
2026-11-14T19:49:17.5550492Z test_available_games_but_none_checked_is_error (test_health_audit.HealthAuditTests.test_available_games_but_none_checked_is_error) ... ok
2026-11-14T19:49:17.5552351Z test_missing_live_matchup_fails (test_health_audit.HealthAuditTests.test_missing_live_matchup_fails) ... ok
2026-11-14T19:49:17.5557620Z test_partial_coverage_warns (test_health_audit.HealthAuditTests.test_partial_coverage_warns) ... ok
2026-11-14T19:49:17.5567740Z test_stale_odds_fails (test_health_audit.HealthAuditTests.test_stale_odds_fails) ... ok
2026-11-14T19:49:17.6844112Z test_completed_games_not_missing (test_slate_matchup_audit.SlateMatchupAuditTests.test_completed_games_not_missing) ... ok
2026-11-14T19:49:17.6845299Z test_missing_dallas_named_without_inventing_lines (test_slate_matchup_audit.SlateMatchupAuditTests.test_missing_dallas_named_without_inventing_lines) ... ok
2026-11-14T19:49:17.6946711Z ##[group]Run python -m unittest discover -s iphone_bot/tests -p 'test_failure_domain_phase.py' -v
2026-11-14T19:49:17.6947328Z [36;1mpython -m unittest discover -s iphone_bot/tests -p 'test_failure_domain_phase.py' -v[0m
2026-11-14T19:49:18.0529358Z test_active_audit_ignores_retired_odds_but_keeps_primary_capture_failure (test_failure_domain_phase.ActiveFeedScopeTests.test_active_audit_ignores_retired_odds_but_keeps_primary_capture_failure) ... ok
2026-11-14T19:49:18.0530395Z test_scheduled_gate_preserves_active_failure_exit_and_artifact (test_failure_domain_phase.ActiveFeedScopeTests.test_scheduled_gate_preserves_active_failure_exit_and_artifact) ... ok
2026-11-14T19:49:18.0626292Z test_only_complete_fresh_verified_posttip_slate_relaxes_offer_freshness (test_failure_domain_phase.FailureDomainPhaseTests.test_only_complete_fresh_verified_posttip_slate_relaxes_offer_freshness) ... ok
2026-11-14T19:49:18.0627791Z test_accounted_and_pending_are_distinguished (test_failure_domain_phase.NBAGradingCoverageTests.test_accounted_and_pending_are_distinguished) ... ok
2026-11-14T19:49:18.0628700Z test_invalid_counts_or_reconciliation_fail_closed (test_failure_domain_phase.NBAGradingCoverageTests.test_invalid_counts_or_reconciliation_fail_closed) ... ok
2026-11-14T19:49:18.1425787Z test_nonobject_json_is_rejected_by_integrated_audit (test_failure_domain_phase.NBAGradingCoverageTests.test_nonobject_json_is_rejected_by_integrated_audit) ... ok
2026-11-14T19:49:18.1428377Z test_real_published_coverage_remains_valid (test_failure_domain_phase.NBAGradingCoverageTests.test_real_published_coverage_remains_valid) ... ok
2026-11-14T19:49:18.1429577Z test_unknown_missing_empty_or_contradictory_status_is_not_success (test_failure_domain_phase.NBAGradingCoverageTests.test_unknown_missing_empty_or_contradictory_status_is_not_success) ... ok
2026-11-14T19:49:18.1447989Z test_zero_only_report_is_not_verified_coverage (test_failure_domain_phase.NBAGradingCoverageTests.test_zero_only_report_is_not_verified_coverage) ... ok
2026-11-14T19:49:18.1705235Z test_actual_standard_pending_remains_visible (test_failure_domain_phase.NFLStandardPendingAuditTests.test_actual_standard_pending_remains_visible) ... ok
2026-11-14T19:49:18.1977472Z test_alternative_pending_is_not_standard_failure (test_failure_domain_phase.NFLStandardPendingAuditTests.test_alternative_pending_is_not_standard_failure) ... ok
2026-11-14T19:49:18.3075010Z test_invalid_standard_pending_fails_closed (test_failure_domain_phase.NFLStandardPendingAuditTests.test_invalid_standard_pending_fails_closed) ... ok
2026-11-14T19:49:18.3255003Z [36;1m# Preserve real active-app failures and their JSON even on exit 1.[0m
2026-11-14T19:49:18.3255214Z [36;1mset -o pipefail[0m
2026-11-14T19:49:18.3255413Z [36;1mpython -m iphone_bot.audit_failure_domains | tee out/feed-health.json[0m
2026-11-14T19:49:18.3865959Z   "status": "DEGRADED",
2026-11-14T19:49:18.3872286Z       "detail": "status=DEGRADED; check published readiness blockers"
2026-11-14T19:49:18.3876924Z       "detail": "Provider board reports complete coverage"
2026-11-14T19:49:18.3878500Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T19:49:18.3934176Z ##[error]Process completed with exit code 1.
2026-11-14T19:49:18.4026365Z   if-no-files-found: error
2026-11-14T19:49:18.7678186Z (node:2199) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
```

## Run 43634109410 / job 132567073238

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634109410

```text
2026-11-14T19:49:09.1499229Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T19:49:09.130415+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage": {"ONLY_AI": 9}}, "issues": ["SOME_SCHEDULED_GAMES_WITHOUT_SAVED_VERIFIED_LINES"], "scope": "NEXT_FUTURE_NBA_SLATE", "real_sportsbook_lines_are_not_guaranteed": true, "is_a_simulated_outcome": false, "note": "Source coverage for the next scheduled NBA date, not a guarantee every player has a priced market. Missing quotes may reflect provider gaps or pre-publication."}
2026-11-14T19:49:09.1579690Z ##[error]Process completed with exit code 1.
2026-11-14T19:49:09.1672738Z ##[group]Run set -euo pipefail
2026-11-14T19:49:09.1673725Z [36;1mset -euo pipefail[0m
2026-11-14T19:49:10.6415413Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T19:49:10.623301+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage": {"ONLY_AI": 9}}, "issues": ["SOME_SCHEDULED_GAMES_WITHOUT_SAVED_VERIFIED_LINES"], "scope": "NEXT_FUTURE_NBA_SLATE", "real_sportsbook_lines_are_not_guaranteed": true, "is_a_simulated_outcome": false, "note": "Source coverage for the next scheduled NBA date, not a guarantee every player has a priced market. Missing quotes may reflect provider gaps or pre-publication."}
2026-11-14T19:49:13.2889061Z [36;1mecho "::error::NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json"[0m
2026-11-14T19:49:13.3173530Z ##[error]NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json
2026-11-14T19:49:13.3175274Z ##[error]Process completed with exit code 1.
```

## Run 43634107622 / job 132567011803

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43634107622

```text
2026-11-14T19:48:58.3933735Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T19:48:58.4010314Z ##[error]Process completed with exit code 2.
2026-11-14T19:48:58.4071188Z ##[group]Run set -euo pipefail
2026-11-14T19:48:58.4071540Z [36;1mset -euo pipefail[0m
2026-11-14T19:48:59.8779850Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T19:49:01.1245739Z ##[error]Process completed with exit code 2.
2026-11-14T19:49:01.1281738Z ##[group]Run echo "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"
2026-11-14T19:49:01.1282576Z [36;1mecho "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"[0m
2026-11-14T19:49:01.1411649Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T19:49:01.1413432Z ##[error]Process completed with exit code 1.
```

## Run 43633809796 / job 132566088708

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43633809796

```text
2026-11-14T19:45:40.0592101Z ##[group]Run set -euo pipefail
2026-11-14T19:45:40.0592534Z [36;1mset -euo pipefail[0m
2026-11-14T19:45:40.0593938Z [36;1m  *) echo "::error::Unexpected Pages mode: $mode"; exit 1 ;;[0m
2026-11-14T19:51:40.6285047Z   "status": "FAIL",
2026-11-14T19:51:40.6364546Z ##[error]Process completed with exit code 1.
2026-11-14T19:51:40.6396522Z [36;1m  echo '::error::Legacy Pages verification did not produce evidence'[0m
```

## Run 43633600810 / job 132565452797

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43633600810

```text
2026-11-14T19:43:17.6357029Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T19:43:44.2976002Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T19:43:18.749708+00:00", "error": null}
2026-11-14T19:43:44.4784827Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T19:43:44.5357876Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:43:44.5422822Z ##[error]Process completed with exit code 2.
2026-11-14T19:43:44.5482497Z ##[group]Run set -euo pipefail
2026-11-14T19:43:44.5482886Z [36;1mset -euo pipefail[0m
2026-11-14T19:43:44.5494356Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T19:43:46.5148143Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:43:48.0866920Z ##[group]Run set -euo pipefail
2026-11-14T19:43:48.0867254Z [36;1mset -euo pipefail[0m
2026-11-14T19:43:48.0872952Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T19:43:48.0875455Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T19:43:48.0875907Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T19:43:48.0876679Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T19:43:48.0877071Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T19:43:48.0878884Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T19:43:48.0879297Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T19:43:48.0881643Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T19:43:48.0884422Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T19:43:48.0885424Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T19:43:48.1261845Z ##[group]Run set -euo pipefail
2026-11-14T19:43:48.1262184Z [36;1mset -euo pipefail[0m
2026-11-14T19:43:48.1263138Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T19:43:48.1274444Z [36;1m  echo "### Failing required components"[0m
2026-11-14T19:43:48.1277560Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T19:43:48.6147813Z   if-no-files-found: error
2026-11-14T19:43:49.1925487Z (node:2485) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:43:50.0268391Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T19:43:50.0376751Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T19:43:50.0378710Z ##[error]Process completed with exit code 1.
```

## Run 43633570219 / job 132565361869

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43633570219

```text
2026-11-14T19:49:25.0709818Z   "status": "FAIL",
2026-11-14T19:49:39.0593570Z       "status": "FAIL",
2026-11-14T19:49:39.0614142Z         "error": "Feed request timed out",
2026-11-14T19:49:39.0710564Z       "name": "missing_games_disclosed",
2026-11-14T19:49:39.0713488Z   "overall": "FAIL"
2026-11-14T19:49:39.5988186Z (node:3338) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:49:40.0419497Z ##[error]Process completed with exit code 1.
```

## Run 43633570219 / job 132565362067

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43633570219

```text
2026-11-14T19:49:38.5073453Z   "status": "FAIL",
2026-11-14T19:49:56.3117525Z       "status": "FAIL",
2026-11-14T19:49:56.3134084Z         "error": "Feed request timed out",
2026-11-14T19:49:56.3234478Z       "name": "missing_games_disclosed",
2026-11-14T19:49:56.3236732Z   "overall": "FAIL"
2026-11-14T19:49:56.9436996Z (node:5182) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:49:57.9152312Z ##[error]Process completed with exit code 1.
```

## Run 43633527679 / job 132565229165

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43633527679

```text
2026-11-14T19:42:27.0526549Z ##[group]Run python -m py_compile iphone_bot/audit_failure_domains.py
2026-11-14T19:42:27.0527226Z [36;1mpython -m py_compile iphone_bot/audit_failure_domains.py[0m
2026-11-14T19:42:27.1565106Z ##[group]Run python -m iphone_bot.audit_failure_domains
2026-11-14T19:42:27.1565582Z [36;1mpython -m iphone_bot.audit_failure_domains[0m
2026-11-14T19:42:27.2627703Z   "status": "DEGRADED",
2026-11-14T19:42:27.2642013Z       "detail": "status=DEGRADED; check published readiness blockers"
2026-11-14T19:42:27.2656954Z       "detail": "Provider board reports complete coverage"
2026-11-14T19:42:27.2661519Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T19:42:27.2711477Z ##[error]Process completed with exit code 1.
```

## Run 43633477842 / job 132565073874

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43633477842

```text
2026-11-14T19:41:54.3853708Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T19:42:19.8504630Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T19:41:54.536802+00:00", "error": null}
2026-11-14T19:42:19.9818956Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T19:42:20.0439663Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:42:20.0508219Z ##[error]Process completed with exit code 2.
2026-11-14T19:42:20.0571062Z ##[group]Run set -euo pipefail
2026-11-14T19:42:20.0571535Z [36;1mset -euo pipefail[0m
2026-11-14T19:42:20.0586799Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T19:42:21.2073894Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:42:23.2631604Z ##[group]Run set -euo pipefail
2026-11-14T19:42:23.2632131Z [36;1mset -euo pipefail[0m
2026-11-14T19:42:23.2639313Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T19:42:23.2642637Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T19:42:23.2643195Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T19:42:23.2644223Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T19:42:23.2644719Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T19:42:23.2647028Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T19:42:23.2647786Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T19:42:23.2650544Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T19:42:23.2654125Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T19:42:23.2655534Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T19:42:23.3059441Z ##[group]Run set -euo pipefail
2026-11-14T19:42:23.3059974Z [36;1mset -euo pipefail[0m
2026-11-14T19:42:23.3061340Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T19:42:23.3075794Z [36;1m  echo "### Failing required components"[0m
2026-11-14T19:42:23.3079534Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T19:42:23.9131039Z   if-no-files-found: error
2026-11-14T19:42:24.3255772Z (node:2468) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:42:24.7091251Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T19:42:24.7210322Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T19:42:24.7212578Z ##[error]Process completed with exit code 1.
```

## Run 43632507241 / job 132562022992

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43632507241

```text
2026-11-14T19:31:10.5087292Z ##[group]Run python -m iphone_bot.audit_primary_model_missing
2026-11-14T19:31:10.5088374Z [36;1mpython -m iphone_bot.audit_primary_model_missing[0m
2026-11-14T19:31:10.8598703Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T19:31:10.821905+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 2, "unique_provider_player_stat_markets": 38, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 76, "standard_source_quotes": 76, "standard_unique_markets": 76, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 15, "missing_primary_with_separate_research_receipt": 15, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 40, "frozen_ai_only": 108, "frozen_line_backed": 61, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 61, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 59, "standard_source_quotes": 59, "standard_unique_markets": 59, "standard_markets_without_frozen_model": 3, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 3, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 3, "unique_provider_player_stat_markets": 41, "frozen_ai_only": 100, "frozen_line_backed": 56, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 56, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 0, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 0, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 36, "frozen_ai_only": 96, "frozen_line_backed": 51, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 51, "issues": []}], "issues": ["Denver Nuggets @ New Orleans Pelicans: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Dallas Mavericks @ Cleveland Cavaliers: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Brooklyn Nets @ Memphis Grizzlies: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Chicago Bulls @ Minnesota Timberwolves: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"], "note": "Provider quotes, AI-only forecasts, line-backed frozen predictions and final grades are separate. Missing records never fabricated.", "summary": {"schedule_games": 5, "games_with_saved_source_quotes": 5, "games_with_frozen_ai": 5, "games_with_line_backed_models": 5, "total_quotes": 311, "total_standard_source_quotes": 311, "total_standard_markets_without_frozen_model": 28, "total_price_moves_from_original_frozen_line": 0, "total_player_stat_markets_never_primary_frozen": 28, "total_missing_primary_with_separate_research_receipt": 23, "total_missing_primary_without_any_ai_receipt": 5, "total_ai_only": 504, "total_line_backed": 283, "total_line_backed_graded": 0, "total_ai_only_graded": 0}, "current_upcoming_coverage": {"status": "INCOMPLETE", "checked_at": "2026-11-14T19:31:10.821905+00:00", "source_generated_at": "2026-11-14T19:12:37.729953+00:00", "verified_current_offers": 174, "matched_primary_offers": 159, "missing_primary_offers": 15, "games": [{"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 37, "matched_primary_offers": 28, "missing_primary_offers": 9, "missing": [{"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PRA", "line": 15.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "REB", "line": 2.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PTS", "line": 10.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "REB", "line": 4.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PTS", "line": 6.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PRA", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PTS", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PRA", "line": 18.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "AST", "line": 3.5}]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 36, "matched_primary_offers": 34, "missing_primary_offers": 2, "missing": [{"player": "Nic Claxton", "team": "CHI", "stat": "PTS", "line": 7.5}, {"player": "Nic Claxton", "team": "CHI", "stat": "PRA", "line": 15.5}]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "verified_current_offers": 35, "matched_primary_offers": 35, "missing_primary_offers": 0, "missing": []}, {"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "verified_current_offers": 34, "matched_primary_offers": 30, "missing_primary_offers": 4, "missing": [{"player": "Cameron Johnson", "team": "DEN", "stat": "PTS", "line": 12.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "PRA", "line": 18.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "REB", "line": 3.5}, {"player": "Spencer Jones", "team": "DEN", "stat": "REB", "line": 2.5}]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 32, "matched_primary_offers": 32, "missing_primary_offers": 0, "missing": []}], "issues": [], "scope": "CURRENT_UPCOMING_STANDARD_OFFERS_ONLY", "research_and_provisional_count_as_primary": false}}
2026-11-14T19:31:10.8660921Z ##[error]Process completed with exit code 1.
2026-11-14T19:31:10.8713610Z ##[group]Run set -euo pipefail
2026-11-14T19:31:10.8713893Z [36;1mset -euo pipefail[0m
2026-11-14T19:31:10.8716319Z [36;1m  python -m iphone_bot.audit_primary_model_missing[0m
2026-11-14T19:31:10.8717297Z [36;1m  git add docs/tonight_capture_gradeability.json docs/primary_model_missing_diagnostics.json[0m
2026-11-14T19:31:10.8718916Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T19:31:12.6005712Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T19:31:12.565877+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 2, "unique_provider_player_stat_markets": 38, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 76, "standard_source_quotes": 76, "standard_unique_markets": 76, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 15, "missing_primary_with_separate_research_receipt": 15, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 40, "frozen_ai_only": 108, "frozen_line_backed": 61, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 61, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 59, "standard_source_quotes": 59, "standard_unique_markets": 59, "standard_markets_without_frozen_model": 3, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 3, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 3, "unique_provider_player_stat_markets": 41, "frozen_ai_only": 100, "frozen_line_backed": 56, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 56, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 51, "standard_source_quotes": 51, "standard_unique_markets": 51, "standard_markets_without_frozen_model": 0, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 0, "missing_primary_with_separate_research_receipt": 0, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 36, "frozen_ai_only": 96, "frozen_line_backed": 51, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 51, "issues": []}], "issues": ["Denver Nuggets @ New Orleans Pelicans: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Dallas Mavericks @ Cleveland Cavaliers: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Brooklyn Nets @ Memphis Grizzlies: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL", "Chicago Bulls @ Minnesota Timberwolves: STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"], "note": "Provider quotes, AI-only forecasts, line-backed frozen predictions and final grades are separate. Missing records never fabricated.", "summary": {"schedule_games": 5, "games_with_saved_source_quotes": 5, "games_with_frozen_ai": 5, "games_with_line_backed_models": 5, "total_quotes": 311, "total_standard_source_quotes": 311, "total_standard_markets_without_frozen_model": 28, "total_price_moves_from_original_frozen_line": 0, "total_player_stat_markets_never_primary_frozen": 28, "total_missing_primary_with_separate_research_receipt": 23, "total_missing_primary_without_any_ai_receipt": 5, "total_ai_only": 504, "total_line_backed": 283, "total_line_backed_graded": 0, "total_ai_only_graded": 0}, "current_upcoming_coverage": {"status": "INCOMPLETE", "checked_at": "2026-11-14T19:31:12.565877+00:00", "source_generated_at": "2026-11-14T19:12:37.729953+00:00", "verified_current_offers": 174, "matched_primary_offers": 159, "missing_primary_offers": 15, "games": [{"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 37, "matched_primary_offers": 28, "missing_primary_offers": 9, "missing": [{"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PRA", "line": 15.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "REB", "line": 2.5}, {"player": "Egor D\u00ebmin", "team": "BKN", "stat": "PTS", "line": 10.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "REB", "line": 4.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PTS", "line": 6.5}, {"player": "Danny Wolf", "team": "BKN", "stat": "PRA", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PTS", "line": 12.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "PRA", "line": 18.5}, {"player": "Mikel Brown Jr.", "team": "BKN", "stat": "AST", "line": 3.5}]}, {"game": "Chicago Bulls @ Minnesota Timberwolves", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 36, "matched_primary_offers": 34, "missing_primary_offers": 2, "missing": [{"player": "Nic Claxton", "team": "CHI", "stat": "PTS", "line": 7.5}, {"player": "Nic Claxton", "team": "CHI", "stat": "PRA", "line": 15.5}]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "verified_current_offers": 35, "matched_primary_offers": 35, "missing_primary_offers": 0, "missing": []}, {"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "verified_current_offers": 34, "matched_primary_offers": 30, "missing_primary_offers": 4, "missing": [{"player": "Cameron Johnson", "team": "DEN", "stat": "PTS", "line": 12.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "PRA", "line": 18.5}, {"player": "Cameron Johnson", "team": "DEN", "stat": "REB", "line": 3.5}, {"player": "Spencer Jones", "team": "DEN", "stat": "REB", "line": 2.5}]}, {"game": "Detroit Pistons @ Miami Heat", "start": "2026-11-15T01:00:00+00:00", "verified_current_offers": 32, "matched_primary_offers": 32, "missing_primary_offers": 0, "missing": []}], "issues": [], "scope": "CURRENT_UPCOMING_STANDARD_OFFERS_ONLY", "research_and_provisional_count_as_primary": false}}
2026-11-14T19:31:14.6085832Z ##[error]Process completed with exit code 1.
2026-11-14T19:31:14.6120824Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T19:31:14.6121972Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T19:31:14.6241505Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T19:31:14.6243062Z ##[error]Process completed with exit code 1.
```

## Run 43632357502 / job 132561618951

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43632357502

```text
2026-11-14T19:29:45.2134921Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T19:29:45.190145+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage": {"ONLY_AI": 9}}, "issues": ["SOME_SCHEDULED_GAMES_WITHOUT_SAVED_VERIFIED_LINES"], "scope": "NEXT_FUTURE_NBA_SLATE", "real_sportsbook_lines_are_not_guaranteed": true, "is_a_simulated_outcome": false, "note": "Source coverage for the next scheduled NBA date, not a guarantee every player has a priced market. Missing quotes may reflect provider gaps or pre-publication."}
2026-11-14T19:29:45.2240573Z ##[error]Process completed with exit code 1.
2026-11-14T19:29:45.2303835Z ##[group]Run set -euo pipefail
2026-11-14T19:29:45.2304197Z [36;1mset -euo pipefail[0m
2026-11-14T19:29:46.7904992Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T19:29:46.767190+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage": {"ONLY_AI": 9}}, "issues": ["SOME_SCHEDULED_GAMES_WITHOUT_SAVED_VERIFIED_LINES"], "scope": "NEXT_FUTURE_NBA_SLATE", "real_sportsbook_lines_are_not_guaranteed": true, "is_a_simulated_outcome": false, "note": "Source coverage for the next scheduled NBA date, not a guarantee every player has a priced market. Missing quotes may reflect provider gaps or pre-publication."}
2026-11-14T19:29:48.3742612Z [36;1mecho "::error::NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json"[0m
2026-11-14T19:29:48.4065290Z ##[error]NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json
2026-11-14T19:29:48.4067390Z ##[error]Process completed with exit code 1.
```

## Run 43632154682 / job 132560966909

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43632154682

```text
2026-11-14T19:27:23.0097345Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T19:27:24.0218517Z {"checked_at": "2026-11-14T19:27:23.073536+00:00", "recoveries": [{"workflow": "nba-new-ai-all-markets.yml", "status": "SKIPPED", "reason": "ACTIVE_RECENT_SUCCESS_OR_FAILURE_BACKOFF"}], "status": "COMPLETE", "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}
2026-11-14T19:27:25.5369989Z (node:2385) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:27:26.0652796Z [36;1m  echo "- **FAIL** Heartbeat report missing; inspect failed workflow and artifact." >> "$GITHUB_STEP_SUMMARY"[0m
2026-11-14T19:27:26.0832161Z ##[group]Run set -euo pipefail
2026-11-14T19:27:26.0832503Z [36;1mset -euo pipefail[0m
2026-11-14T19:27:26.0836606Z [36;1mgh label create pipeline-alert --color B60205 --description "Dame's Picks pipeline failure" 2>/dev/null || true[0m
2026-11-14T19:27:26.0838346Z [36;1m  title="[pipeline] $stage failing"[0m
2026-11-14T19:27:26.0839902Z [36;1m  if [ "$status" = FAIL ] && [ -z "$issue" ]; then[0m
2026-11-14T19:27:26.4811053Z ##[error]Process completed with exit code 1.
```

## Run 43632154672 / job 132561119087

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43632154672

```text
2026-11-14T19:27:55.1654417Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T19:28:20.7620517Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T19:27:55.312159+00:00", "error": null}
2026-11-14T19:28:20.8268370Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T19:28:20.8673775Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:28:20.8716850Z ##[error]Process completed with exit code 2.
2026-11-14T19:28:20.8754420Z ##[group]Run set -euo pipefail
2026-11-14T19:28:20.8754614Z [36;1mset -euo pipefail[0m
2026-11-14T19:28:20.8760808Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T19:28:21.3148377Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T19:28:22.9187895Z ##[group]Run set -euo pipefail
2026-11-14T19:28:22.9188108Z [36;1mset -euo pipefail[0m
2026-11-14T19:28:22.9191358Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T19:28:22.9192756Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T19:28:22.9193010Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T19:28:22.9193441Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T19:28:22.9193666Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T19:28:22.9194725Z [36;1m  # request failed: avoid repeatedly spending top-up credits.[0m
2026-11-14T19:28:22.9194958Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T19:28:22.9196139Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T19:28:22.9197756Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T19:28:22.9198316Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T19:28:22.9494156Z ##[group]Run set -euo pipefail
2026-11-14T19:28:22.9494350Z [36;1mset -euo pipefail[0m
2026-11-14T19:28:22.9494841Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T19:28:22.9501060Z [36;1m  echo "### Failing required components"[0m
2026-11-14T19:28:22.9502750Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T19:28:23.5618897Z   if-no-files-found: error
2026-11-14T19:28:24.0069010Z (node:2276) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T19:28:24.6353770Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T19:28:24.6467002Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T19:28:24.6468224Z ##[error]Process completed with exit code 1.
```
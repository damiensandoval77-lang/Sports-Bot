# Failed jobs and observed error excerpts

## verify-readiness — run 43640580321, job 132587146198

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43640580321/job/132587146198

```text
2026-11-14T21:02:04.3479118Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T21:02:08.9749568Z (node:2402) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:02:08.9750612Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:02:08.9969359Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T21:02:34.7793751Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T21:02:09.187673+00:00", "error": null}
2026-11-14T21:02:34.7948802Z ##[group]Run # Free official NBA liveData only. Partial authentic observations
2026-11-14T21:02:34.7949413Z [36;1m# Free official NBA liveData only. Partial authentic observations[0m
2026-11-14T21:02:34.9270943Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T21:02:34.9960323Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T21:02:35.0031039Z ##[error]Process completed with exit code 2.
2026-11-14T21:02:35.0094301Z ##[group]Run set -euo pipefail
2026-11-14T21:02:35.0094711Z [36;1mset -euo pipefail[0m
2026-11-14T21:02:35.0106881Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T21:02:36.8915926Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T21:02:38.2031997Z ##[group]Run set -euo pipefail
2026-11-14T21:02:38.2032380Z [36;1mset -euo pipefail[0m
2026-11-14T21:02:38.2038516Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T21:02:38.2041173Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T21:02:38.2041651Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T21:02:38.2042478Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T21:02:38.2042892Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T21:02:38.2044943Z [36;1m  # request failed: avoid hammering a denied public endpoint.[0m
2026-11-14T21:02:38.2045616Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T21:02:38.2047901Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T21:02:38.2050897Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T21:02:38.2051959Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T21:02:39.5116994Z Skipping nba-prizepicks-full-slate.yml: active, successful cooldown, or failure backoff (paid calls hard-capped)
2026-11-14T21:02:39.5178597Z ##[group]Run set -euo pipefail
2026-11-14T21:02:39.5179213Z [36;1mset -euo pipefail[0m
2026-11-14T21:02:39.5180917Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T21:02:39.5184068Z [36;1m  echo "::warning::GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary."[0m
2026-11-14T21:02:39.5203214Z [36;1m  echo "### Failing required components"[0m
2026-11-14T21:02:39.5209784Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T21:02:39.9572352Z ##[warning]GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary.
2026-11-14T21:02:39.9671225Z   if-no-files-found: error
2026-11-14T21:02:40.1421564Z (node:2494) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:02:40.1422545Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:02:40.4589262Z (node:2494) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T21:02:41.0000139Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T21:02:41.0154362Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T21:02:41.0157250Z ##[error]Process completed with exit code 1.
2026-11-14T21:02:41.3216891Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify — run 43640580171, job 132587046808

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43640580171/job/132587046808

```text
2026-11-14T21:01:43.7473062Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T21:01:48.1801785Z (node:2379) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:01:48.1802817Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:01:48.3687908Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T21:01:48.3759673Z ##[error]Process completed with exit code 2.
2026-11-14T21:01:48.3823777Z ##[group]Run set -euo pipefail
2026-11-14T21:01:48.3824139Z [36;1mset -euo pipefail[0m
2026-11-14T21:01:49.9830192Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T21:01:51.2679493Z ##[error]Process completed with exit code 2.
2026-11-14T21:01:51.2728692Z ##[group]Run echo "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"
2026-11-14T21:01:51.2729677Z [36;1mecho "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"[0m
2026-11-14T21:01:51.2868273Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T21:01:51.2870232Z ##[error]Process completed with exit code 1.
2026-11-14T21:01:51.5697963Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## heartbeat — run 43640548864, job 132586950171

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43640548864/job/132586950171

```text
2026-11-14T21:01:23.2934324Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T21:01:27.6283915Z (node:2124) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:01:27.6285055Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:01:30.7324152Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T21:01:31.8971492Z {"checked_at": "2026-11-14T21:01:30.785180+00:00", "recoveries": [{"workflow": "nba-new-ai-all-markets.yml", "status": "SKIPPED", "reason": "ACTIVE_RECENT_SUCCESS_OR_FAILURE_BACKOFF"}], "status": "COMPLETE", "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}
2026-11-14T21:01:33.2536958Z (node:2153) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:01:33.2538014Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:01:36.7845240Z (node:2153) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T21:01:37.3778547Z [36;1m  echo "- **FAIL** Heartbeat report missing; inspect failed workflow and artifact." >> "$GITHUB_STEP_SUMMARY"[0m
2026-11-14T21:01:37.3928840Z ##[group]Run set -euo pipefail
2026-11-14T21:01:37.3929223Z [36;1mset -euo pipefail[0m
2026-11-14T21:01:37.3931502Z [36;1m  echo "::warning::GitHub Issues disabled or unavailable; alert evidence remains in the run summary and artifact."[0m
2026-11-14T21:01:37.3932659Z [36;1mgh label create pipeline-alert --color B60205 --description "Dame's Picks pipeline failure" 2>/dev/null || true[0m
2026-11-14T21:01:37.3934305Z [36;1m  title="[pipeline] $stage failing"[0m
2026-11-14T21:01:37.3935933Z [36;1m  if [ "$status" = FAIL ] && [ -z "$issue" ]; then[0m
2026-11-14T21:01:37.7951131Z ##[warning]GitHub Issues disabled or unavailable; alert evidence remains in the run summary and artifact.
2026-11-14T21:01:37.8058476Z ##[error]Process completed with exit code 1.
2026-11-14T21:01:38.0226669Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## audit — run 43640548825, job 132586950110

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43640548825/job/132586950110

```text
2026-11-14T21:01:23.4592921Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T21:01:28.2982770Z (node:2856) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:01:28.2983648Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:01:28.8064921Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T21:01:28.758510+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 9, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 9, "missing_primary_with_separate_research_receipt": 4, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 52, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 52, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 17, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 17, "missing_prim
2026-11-14T21:01:28.8133278Z ##[error]Process completed with exit code 1.
2026-11-14T21:01:28.8198801Z ##[group]Run set -euo pipefail
2026-11-14T21:01:28.8199145Z [36;1mset -euo pipefail[0m
2026-11-14T21:01:28.8205675Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T21:01:29.6805102Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T21:01:29.635248+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 9, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 9, "missing_primary_with_separate_research_receipt": 4, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 52, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 52, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 17, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 17, "missing_prim
2026-11-14T21:01:30.9435548Z ##[error]Process completed with exit code 1.
2026-11-14T21:01:30.9481288Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T21:01:30.9483064Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T21:01:30.9624049Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T21:01:30.9625940Z ##[error]Process completed with exit code 1.
2026-11-14T21:01:31.2531064Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## source-readiness — run 43640548809, job 132587010432

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43640548809/job/132587010432

```text
2026-11-14T21:01:36.7939891Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T21:01:41.2104096Z (node:2188) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:01:41.2104943Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:01:41.5169685Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T21:01:41.498632+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage"
2026-11-14T21:01:41.5263535Z ##[error]Process completed with exit code 1.
2026-11-14T21:01:41.5316636Z ##[group]Run set -euo pipefail
2026-11-14T21:01:41.5317034Z [36;1mset -euo pipefail[0m
2026-11-14T21:01:41.5322755Z [36;1m  python -c "import json; r=json.load(open('docs/pregame_lifecycle_readiness.json')); assert r.get('status') in ('READY','NOT_READY')"[0m
2026-11-14T21:01:41.9818495Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T21:01:41.963490+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage"
2026-11-14T21:01:43.2790254Z [36;1mecho "::error::NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json"[0m
2026-11-14T21:01:43.3065761Z ##[error]NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json
2026-11-14T21:01:43.3067599Z ##[error]Process completed with exit code 1.
2026-11-14T21:01:43.5334648Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify-readiness — run 43640548803, job 132586950061

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43640548803/job/132586950061

```text
2026-11-14T21:01:22.7116590Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T21:01:27.2021330Z (node:2393) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:01:27.2022703Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:01:27.2248415Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T21:01:53.0061794Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T21:01:27.392314+00:00", "error": null}
2026-11-14T21:01:53.0220016Z ##[group]Run # Free official NBA liveData only. Partial authentic observations
2026-11-14T21:01:53.0220641Z [36;1m# Free official NBA liveData only. Partial authentic observations[0m
2026-11-14T21:01:53.0962880Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T21:01:53.1563787Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T21:01:53.1631384Z ##[error]Process completed with exit code 2.
2026-11-14T21:01:53.1698670Z ##[group]Run set -euo pipefail
2026-11-14T21:01:53.1699137Z [36;1mset -euo pipefail[0m
2026-11-14T21:01:53.1713951Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T21:01:53.6504461Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T21:01:54.9809015Z ##[group]Run set -euo pipefail
2026-11-14T21:01:54.9809555Z [36;1mset -euo pipefail[0m
2026-11-14T21:01:54.9816391Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T21:01:54.9819528Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T21:01:54.9820041Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T21:01:54.9820952Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T21:01:54.9821419Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T21:01:54.9824166Z [36;1m  # request failed: avoid hammering a denied public endpoint.[0m
2026-11-14T21:01:54.9824674Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T21:01:54.9827091Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T21:01:54.9830511Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T21:01:54.9831773Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T21:01:56.1092383Z Skipping nba-prizepicks-full-slate.yml: active, successful cooldown, or failure backoff (paid calls hard-capped)
2026-11-14T21:01:56.1154483Z ##[group]Run set -euo pipefail
2026-11-14T21:01:56.1155248Z [36;1mset -euo pipefail[0m
2026-11-14T21:01:56.1157000Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T21:01:56.1159820Z [36;1m  echo "::warning::GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary."[0m
2026-11-14T21:01:56.1177892Z [36;1m  echo "### Failing required components"[0m
2026-11-14T21:01:56.1184118Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T21:01:56.5077782Z ##[warning]GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary.
2026-11-14T21:01:56.5201977Z   if-no-files-found: error
2026-11-14T21:01:56.6846696Z (node:2481) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:01:56.6847458Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:01:56.9490069Z (node:2481) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T21:01:57.4132444Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T21:01:57.4250703Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T21:01:57.4253264Z ##[error]Process completed with exit code 1.
2026-11-14T21:01:57.6778806Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## audit — run 43640432862, job 132586623487

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43640432862/job/132586623487

```text
2026-11-14T21:00:15.9472197Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T21:00:19.9573695Z (node:2189) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T21:00:19.9574208Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T21:00:20.2751609Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T21:00:20.242825+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 9, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 9, "missing_primary_with_separate_research_receipt": 4, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 52, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 52, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 17, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 17, "missing_prim
2026-11-14T21:00:20.2821581Z ##[error]Process completed with exit code 1.
2026-11-14T21:00:20.2867244Z ##[group]Run set -euo pipefail
2026-11-14T21:00:20.2867478Z [36;1mset -euo pipefail[0m
2026-11-14T21:00:20.2871692Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T21:00:21.8989289Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T21:00:21.865033+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 9, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 9, "missing_primary_with_separate_research_receipt": 4, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 52, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 52, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 17, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 17, "missing_prim
2026-11-14T21:00:23.3272633Z ##[error]Process completed with exit code 1.
2026-11-14T21:00:23.3303282Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T21:00:23.3303913Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T21:00:23.3417372Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T21:00:23.3418699Z ##[error]Process completed with exit code 1.
2026-11-14T21:00:23.5420997Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify-readiness — run 43639881533, job 132584876435

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639881533/job/132584876435

```text
2026-11-14T20:53:41.6212760Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:53:45.6791611Z (node:2197) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:53:45.6792304Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:53:45.6998515Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T20:54:11.5474586Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T20:53:46.157632+00:00", "error": null}
2026-11-14T20:54:11.5588496Z ##[group]Run # Free official NBA liveData only. Partial authentic observations
2026-11-14T20:54:11.5588815Z [36;1m# Free official NBA liveData only. Partial authentic observations[0m
2026-11-14T20:54:11.6647947Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T20:54:11.7074658Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:54:11.7122567Z ##[error]Process completed with exit code 2.
2026-11-14T20:54:11.7160398Z ##[group]Run set -euo pipefail
2026-11-14T20:54:11.7160604Z [36;1mset -euo pipefail[0m
2026-11-14T20:54:11.7167210Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T20:54:13.0649392Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:54:14.4527974Z ##[group]Run set -euo pipefail
2026-11-14T20:54:14.4528197Z [36;1mset -euo pipefail[0m
2026-11-14T20:54:14.4531353Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T20:54:14.4532832Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T20:54:14.4533099Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T20:54:14.4533553Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T20:54:14.4533792Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T20:54:14.4534936Z [36;1m  # request failed: avoid hammering a denied public endpoint.[0m
2026-11-14T20:54:14.4535179Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T20:54:14.4536427Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T20:54:14.4538209Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T20:54:14.4538803Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T20:54:15.8559882Z Skipping nba-prizepicks-full-slate.yml: active, successful cooldown, or failure backoff (paid calls hard-capped)
2026-11-14T20:54:15.8588922Z ##[group]Run set -euo pipefail
2026-11-14T20:54:15.8589135Z [36;1mset -euo pipefail[0m
2026-11-14T20:54:15.8589652Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T20:54:15.8590572Z [36;1m  echo "::warning::GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary."[0m
2026-11-14T20:54:15.8596140Z [36;1m  echo "### Failing required components"[0m
2026-11-14T20:54:15.8598082Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T20:54:16.3170522Z ##[warning]GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary.
2026-11-14T20:54:16.3228985Z   if-no-files-found: error
2026-11-14T20:54:16.4274712Z (node:2279) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:54:16.4275314Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:54:16.7785600Z (node:2279) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:54:17.4149834Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T20:54:17.4269325Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T20:54:17.4270950Z ##[error]Process completed with exit code 1.
2026-11-14T20:54:17.6222331Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify — run 43639881443, job 132584876049

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639881443/job/132584876049

```text
2026-11-14T20:53:40.7423475Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:53:44.9999664Z (node:2197) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:53:45.0001376Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:53:45.5927786Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:53:45.5985964Z ##[error]Process completed with exit code 2.
2026-11-14T20:53:45.6045289Z ##[group]Run set -euo pipefail
2026-11-14T20:53:45.6045678Z [36;1mset -euo pipefail[0m
2026-11-14T20:53:46.9698544Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:53:48.2642438Z ##[error]Process completed with exit code 2.
2026-11-14T20:53:48.2686234Z ##[group]Run echo "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"
2026-11-14T20:53:48.2686929Z [36;1mecho "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"[0m
2026-11-14T20:53:48.2778523Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T20:53:48.2780329Z ##[error]Process completed with exit code 1.
2026-11-14T20:53:48.4819376Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## audit — run 43639857420, job 132584795962

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639857420/job/132584795962

```text
2026-11-14T20:53:24.0488230Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:53:28.2992193Z (node:2193) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:53:28.2993414Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:53:28.6923895Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:53:28.647354+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 9, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 9, "missing_primary_with_separate_research_receipt": 4, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 52, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 52, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 17, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 17, "missing_prim
2026-11-14T20:53:28.6977208Z ##[error]Process completed with exit code 1.
2026-11-14T20:53:28.7026352Z ##[group]Run set -euo pipefail
2026-11-14T20:53:28.7026651Z [36;1mset -euo pipefail[0m
2026-11-14T20:53:28.7032144Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T20:53:29.8792873Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:53:29.844499+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 9, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 9, "missing_primary_with_separate_research_receipt": 4, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 52, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 52, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 17, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 17, "missing_prim
2026-11-14T20:53:31.1488770Z ##[error]Process completed with exit code 1.
2026-11-14T20:53:31.1529935Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T20:53:31.1530804Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T20:53:31.1649446Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T20:53:31.1650914Z ##[error]Process completed with exit code 1.
2026-11-14T20:53:31.3827226Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## audit — run 43639640649, job 132584096406

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639640649/job/132584096406

```text
2026-11-14T20:50:54.2471304Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:50:59.0286656Z (node:2855) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:59.0287384Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:59.5060788Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:50:59.457070+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 9, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 9, "missing_primary_with_separate_research_receipt": 4, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 52, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 52, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 17, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 17, "missing_prim
2026-11-14T20:50:59.5136097Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:59.5198433Z ##[group]Run set -euo pipefail
2026-11-14T20:50:59.5199067Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:59.5205524Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T20:51:01.5079585Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:51:01.462045+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 9, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 9, "missing_primary_with_separate_research_receipt": 4, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 52, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 52, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 17, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 17, "missing_prim
2026-11-14T20:51:02.8303796Z ##[error]Process completed with exit code 1.
2026-11-14T20:51:02.8354327Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T20:51:02.8356262Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T20:51:02.8527997Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T20:51:02.8530830Z ##[error]Process completed with exit code 1.
2026-11-14T20:51:03.2284132Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify-readiness — run 43639636001, job 132584191197

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639636001/job/132584191197

```text
2026-11-14T20:51:14.4459022Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:51:19.0841699Z (node:2571) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:51:19.0842820Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:51:19.1082421Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T20:51:44.7390246Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T20:51:19.299801+00:00", "error": null}
2026-11-14T20:51:44.7544022Z ##[group]Run # Free official NBA liveData only. Partial authentic observations
2026-11-14T20:51:44.7544607Z [36;1m# Free official NBA liveData only. Partial authentic observations[0m
2026-11-14T20:51:44.8416528Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T20:51:44.9136225Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:51:44.9215918Z ##[error]Process completed with exit code 2.
2026-11-14T20:51:44.9282989Z ##[group]Run set -euo pipefail
2026-11-14T20:51:44.9283441Z [36;1mset -euo pipefail[0m
2026-11-14T20:51:44.9295727Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T20:51:46.7309857Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:51:47.9045117Z ##[group]Run set -euo pipefail
2026-11-14T20:51:47.9045486Z [36;1mset -euo pipefail[0m
2026-11-14T20:51:47.9051683Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T20:51:47.9054388Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T20:51:47.9054879Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T20:51:47.9055726Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T20:51:47.9056157Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T20:51:47.9058253Z [36;1m  # request failed: avoid hammering a denied public endpoint.[0m
2026-11-14T20:51:47.9058702Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T20:51:47.9061306Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T20:51:47.9064332Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T20:51:47.9065394Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T20:51:49.1561149Z Skipping nba-prizepicks-full-slate.yml: active, successful cooldown, or failure backoff (paid calls hard-capped)
2026-11-14T20:51:49.1601642Z ##[group]Run set -euo pipefail
2026-11-14T20:51:49.1602050Z [36;1mset -euo pipefail[0m
2026-11-14T20:51:49.1603019Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T20:51:49.1604739Z [36;1m  echo "::warning::GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary."[0m
2026-11-14T20:51:49.1615449Z [36;1m  echo "### Failing required components"[0m
2026-11-14T20:51:49.1619045Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T20:51:49.5742251Z ##[warning]GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary.
2026-11-14T20:51:49.5836000Z   if-no-files-found: error
2026-11-14T20:51:49.7558003Z (node:2657) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:51:49.7559233Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:51:50.0416858Z (node:2657) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:51:50.5386779Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T20:51:50.5540892Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T20:51:50.5543382Z ##[error]Process completed with exit code 1.
2026-11-14T20:51:50.8333954Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify — run 43639635901, job 132584076891

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639635901/job/132584076891

```text
2026-11-14T20:50:50.1535460Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:50:54.5990214Z (node:2374) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:54.5991512Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:54.7880622Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:50:54.7957247Z ##[error]Process completed with exit code 2.
2026-11-14T20:50:54.8024502Z ##[group]Run set -euo pipefail
2026-11-14T20:50:54.8024866Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:56.2709361Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:50:57.5767924Z ##[error]Process completed with exit code 2.
2026-11-14T20:50:57.5812167Z ##[group]Run echo "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"
2026-11-14T20:50:57.5813040Z [36;1mecho "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"[0m
2026-11-14T20:50:57.5950549Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T20:50:57.5952319Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:57.8766599Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## heartbeat — run 43639619038, job 132584056420

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639619038/job/132584056420

```text
2026-11-14T20:50:51.1135245Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:50:55.6459659Z (node:2170) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:55.6460315Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:58.1959625Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T20:51:01.3539702Z {"checked_at": "2026-11-14T20:50:58.311613+00:00", "recoveries": [{"workflow": "nba-new-ai-all-markets.yml", "status": "SKIPPED", "reason": "ACTIVE_RECENT_SUCCESS_OR_FAILURE_BACKOFF"}], "status": "COMPLETE", "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}
2026-11-14T20:51:02.2722691Z (node:2198) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:51:02.2723348Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:51:02.8989672Z (node:2198) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:51:03.3121446Z [36;1m  echo "- **FAIL** Heartbeat report missing; inspect failed workflow and artifact." >> "$GITHUB_STEP_SUMMARY"[0m
2026-11-14T20:51:03.3281408Z ##[group]Run set -euo pipefail
2026-11-14T20:51:03.3281748Z [36;1mset -euo pipefail[0m
2026-11-14T20:51:03.3283872Z [36;1m  echo "::warning::GitHub Issues disabled or unavailable; alert evidence remains in the run summary and artifact."[0m
2026-11-14T20:51:03.3285023Z [36;1mgh label create pipeline-alert --color B60205 --description "Dame's Picks pipeline failure" 2>/dev/null || true[0m
2026-11-14T20:51:03.3286964Z [36;1m  title="[pipeline] $stage failing"[0m
2026-11-14T20:51:03.3288282Z [36;1m  if [ "$status" = FAIL ] && [ -z "$issue" ]; then[0m
2026-11-14T20:51:03.6407642Z ##[warning]GitHub Issues disabled or unavailable; alert evidence remains in the run summary and artifact.
2026-11-14T20:51:03.6527813Z ##[error]Process completed with exit code 1.
2026-11-14T20:51:03.8381131Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## source-readiness — run 43639598468, job 132584000425

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639598468/job/132584000425

```text
2026-11-14T20:50:39.3617977Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:50:44.3883569Z (node:2379) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:44.3884263Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:46.6001312Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T20:50:46.583386+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage"
2026-11-14T20:50:46.6106433Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:46.6157004Z ##[group]Run set -euo pipefail
2026-11-14T20:50:46.6157540Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:46.6161292Z [36;1m  python -c "import json; r=json.load(open('docs/pregame_lifecycle_readiness.json')); assert r.get('status') in ('READY','NOT_READY')"[0m
2026-11-14T20:50:47.9820715Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T20:50:47.965466+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage"
2026-11-14T20:50:49.3197951Z [36;1mecho "::error::NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json"[0m
2026-11-14T20:50:49.3424733Z ##[error]NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json
2026-11-14T20:50:49.3426768Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:49.5273338Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## heartbeat — run 43639598438, job 132583957025

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639598438/job/132583957025

```text
2026-11-14T20:50:24.3063116Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:50:28.7373178Z (node:2125) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:28.7374070Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:30.7349991Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T20:50:34.7577209Z {"checked_at": "2026-11-14T20:50:30.785373+00:00", "recoveries": [{"workflow": "nba-new-ai-all-markets.yml", "status": "SKIPPED", "reason": "ACTIVE_RECENT_SUCCESS_OR_FAILURE_BACKOFF"}], "status": "COMPLETE", "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}
2026-11-14T20:50:35.9630616Z (node:2157) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:35.9631281Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:36.2956660Z (node:2157) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:50:36.9468823Z [36;1m  echo "- **FAIL** Heartbeat report missing; inspect failed workflow and artifact." >> "$GITHUB_STEP_SUMMARY"[0m
2026-11-14T20:50:36.9620571Z ##[group]Run set -euo pipefail
2026-11-14T20:50:36.9620837Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:36.9622781Z [36;1m  echo "::warning::GitHub Issues disabled or unavailable; alert evidence remains in the run summary and artifact."[0m
2026-11-14T20:50:36.9623709Z [36;1mgh label create pipeline-alert --color B60205 --description "Dame's Picks pipeline failure" 2>/dev/null || true[0m
2026-11-14T20:50:36.9625023Z [36;1m  title="[pipeline] $stage failing"[0m
2026-11-14T20:50:36.9626193Z [36;1m  if [ "$status" = FAIL ] && [ -z "$issue" ]; then[0m
2026-11-14T20:50:37.3286074Z ##[warning]GitHub Issues disabled or unavailable; alert evidence remains in the run summary and artifact.
2026-11-14T20:50:37.3388810Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:37.5672955Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## audit — run 43639598429, job 132583990903

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639598429/job/132583990903

```text
2026-11-14T20:50:32.0577720Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:50:36.4777785Z (node:2192) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:36.4781028Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:36.8870045Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:50:36.816888+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 5, "standard_player_stat_markets_never_primary_frozen": 10, "missing_primary_with_separate_research_receipt": 10, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 28, "standard_price_moves_from_original_frozen_line": 8, "standard_player_stat_markets_never_primary_frozen": 20, "missing_p
2026-11-14T20:50:36.8933642Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:36.9386516Z ##[group]Run set -euo pipefail
2026-11-14T20:50:36.9386968Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:36.9394841Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T20:50:38.5706292Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:50:38.530904+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 5, "standard_player_stat_markets_never_primary_frozen": 10, "missing_primary_with_separate_research_receipt": 10, "missing_primary_without_any_ai_receipt": 5, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 28, "standard_price_moves_from_original_frozen_line": 8, "standard_player_stat_markets_never_primary_frozen": 20, "missing_p
2026-11-14T20:50:39.9403450Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:39.9443335Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T20:50:39.9444203Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T20:50:39.9566603Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T20:50:39.9568235Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:40.1947543Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify-readiness — run 43639598372, job 132583984765

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639598372/job/132583984765

```text
2026-11-14T20:50:29.7977641Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:50:33.7647723Z (node:2199) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:33.7648492Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:33.7843685Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T20:51:00.4113631Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T20:50:34.805923+00:00", "error": null}
2026-11-14T20:51:00.4246384Z ##[group]Run # Free official NBA liveData only. Partial authentic observations
2026-11-14T20:51:00.4246733Z [36;1m# Free official NBA liveData only. Partial authentic observations[0m
2026-11-14T20:51:00.5810631Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T20:51:00.6308535Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:51:00.6369017Z ##[error]Process completed with exit code 2.
2026-11-14T20:51:00.6414979Z ##[group]Run set -euo pipefail
2026-11-14T20:51:00.6415263Z [36;1mset -euo pipefail[0m
2026-11-14T20:51:00.6422265Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T20:51:01.9346831Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:51:03.0037401Z  ! [remote rejected] HEAD -> main (cannot lock ref 'refs/heads/main': is at 35267cdf1922d78b5a6cf576db555953e000df25 but expected 95b23b35b436dd1b5ae4db18744903076f366663)
2026-11-14T20:51:03.0037960Z error: failed to push some refs to 'https://github.com/damiensandoval77-lang/Sports-Bot'
2026-11-14T20:51:03.4613706Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:51:04.6495185Z ##[group]Run set -euo pipefail
2026-11-14T20:51:04.6495412Z [36;1mset -euo pipefail[0m
2026-11-14T20:51:04.6498798Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T20:51:04.6500485Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T20:51:04.6500758Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T20:51:04.6501228Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T20:51:04.6501477Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T20:51:04.6502544Z [36;1m  # request failed: avoid hammering a denied public endpoint.[0m
2026-11-14T20:51:04.6502792Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T20:51:04.6504090Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T20:51:04.6505830Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T20:51:04.6506433Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T20:51:05.8801532Z Skipping nba-prizepicks-full-slate.yml: active, successful cooldown, or failure backoff (paid calls hard-capped)
2026-11-14T20:51:05.8831858Z ##[group]Run set -euo pipefail
2026-11-14T20:51:05.8832092Z [36;1mset -euo pipefail[0m
2026-11-14T20:51:05.8832629Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T20:51:05.8833619Z [36;1m  echo "::warning::GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary."[0m
2026-11-14T20:51:05.8839410Z [36;1m  echo "### Failing required components"[0m
2026-11-14T20:51:05.8841497Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T20:51:06.2587556Z ##[warning]GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary.
2026-11-14T20:51:06.2653392Z   if-no-files-found: error
2026-11-14T20:51:06.3836687Z (node:2309) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:51:06.3837364Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:51:06.6915783Z (node:2309) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:51:07.2079559Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T20:51:07.2204032Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T20:51:07.2205544Z ##[error]Process completed with exit code 1.
2026-11-14T20:51:07.4286579Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## audit — run 43639582803, job 132583912160

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639582803/job/132583912160

```text
2026-11-14T20:50:13.9839839Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:50:18.2321530Z (node:2210) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:18.2322091Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:19.0703020Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:50:19.029841+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 5, "standard_player_stat_markets_never_primary_frozen": 10, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 12, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 28, "standard_price_moves_from_original_frozen_line": 8, "standard_player_stat_markets_never_primary_frozen": 20, "missing_p
2026-11-14T20:50:19.0764204Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:19.0815680Z ##[group]Run set -euo pipefail
2026-11-14T20:50:19.0815961Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:19.0820844Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T20:50:20.5616266Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:50:20.525051+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 5, "standard_player_stat_markets_never_primary_frozen": 10, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 12, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 28, "standard_price_moves_from_original_frozen_line": 8, "standard_player_stat_markets_never_primary_frozen": 20, "missing_p
2026-11-14T20:50:21.0228859Z  ! [rejected]        HEAD -> main (fetch first)
2026-11-14T20:50:21.0229444Z error: failed to push some refs to 'https://github.com/damiensandoval77-lang/Sports-Bot'
2026-11-14T20:50:21.0237297Z hint: Updates were rejected because the remote contains work that you do not
2026-11-14T20:50:21.5854697Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:50:21.548452+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 5, "standard_player_stat_markets_never_primary_frozen": 10, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 12, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 28, "standard_price_moves_from_original_frozen_line": 8, "standard_player_stat_markets_never_primary_frozen": 20, "missing_p
2026-11-14T20:50:23.3763752Z  ! [remote rejected] HEAD -> main (cannot lock ref 'refs/heads/main': is at ffd52368021bfd7afe261f5af33b026c7b03990d but expected 749aca3c5c83494a5e7ba95de95fd3abdf8f90c4)
2026-11-14T20:50:23.3765026Z error: failed to push some refs to 'https://github.com/damiensandoval77-lang/Sports-Bot'
2026-11-14T20:50:23.9052621Z TONIGHT_CAPTURE_GRADEABILITY {"checked_at": "2026-11-14T20:50:23.867163+00:00", "game_date_eastern": "2026-11-14", "status": "CAPTURE_INCOMPLETE", "games": [{"game": "Denver Nuggets @ New Orleans Pelicans", "start": "2026-11-15T00:00:00+00:00", "source_quotes": 61, "standard_source_quotes": 61, "standard_unique_markets": 61, "standard_markets_without_frozen_model": 15, "standard_price_moves_from_original_frozen_line": 5, "standard_player_stat_markets_never_primary_frozen": 10, "missing_primary_with_separate_research_receipt": 3, "missing_primary_without_any_ai_receipt": 12, "unique_provider_player_stat_markets": 43, "frozen_ai_only": 96, "frozen_line_backed": 46, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 46, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Dallas Mavericks @ Cleveland Cavaliers", "start": "2026-11-15T00:30:00+00:00", "source_quotes": 74, "standard_source_quotes": 74, "standard_unique_markets": 74, "standard_markets_without_frozen_model": 5, "standard_price_moves_from_original_frozen_line": 0, "standard_player_stat_markets_never_primary_frozen": 5, "missing_primary_with_separate_research_receipt": 5, "missing_primary_without_any_ai_receipt": 0, "unique_provider_player_stat_markets": 46, "frozen_ai_only": 104, "frozen_line_backed": 69, "line_backed_graded": 0, "ai_only_graded": 0, "line_backed_pending": 69, "issues": ["STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"]}, {"game": "Brooklyn Nets @ Memphis Grizzlies", "start": "2026-11-15T01:00:00+00:00", "source_quotes": 89, "standard_source_quotes": 89, "standard_unique_markets": 89, "standard_markets_without_frozen_model": 28, "standard_price_moves_from_original_frozen_line": 8, "standard_player_stat_markets_never_primary_frozen": 20, "missing_p
2026-11-14T20:50:24.9465916Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:24.9497730Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T20:50:24.9498631Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T20:50:24.9613884Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T20:50:24.9615743Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:25.1948324Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify-readiness — run 43639491827, job 132583772541

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639491827/job/132583772541

```text
2026-11-14T20:49:46.0403771Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:49:50.6347884Z (node:2881) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:49:50.6349226Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:49:50.6550379Z [36;1m# This is best effort; readiness still fails if fresh LIVE scores are missing.[0m
2026-11-14T20:50:16.3647979Z {"status": "OBSERVED_NBA_LIVE_SCOREBOARD", "total_games": 5, "generated_at": "2026-11-14T20:49:50.852310+00:00", "error": null}
2026-11-14T20:50:16.3818001Z ##[group]Run # Free official NBA liveData only. Partial authentic observations
2026-11-14T20:50:16.3818597Z [36;1m# Free official NBA liveData only. Partial authentic observations[0m
2026-11-14T20:50:16.4658883Z {"status": "WAITING_FOR_SCHEDULED_TIPOFF", "date": "2026-11-14", "observed_games": 0, "errors": []}
2026-11-14T20:50:16.5320512Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:50:16.5384404Z ##[error]Process completed with exit code 2.
2026-11-14T20:50:16.5463408Z ##[group]Run set -euo pipefail
2026-11-14T20:50:16.5463819Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:16.5475998Z [36;1m  # merge. Exit 2 is an honest degraded report, not a script crash.[0m
2026-11-14T20:50:18.2902584Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T20:50:19.5810008Z ##[group]Run set -euo pipefail
2026-11-14T20:50:19.5810375Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:19.5816392Z [36;1m    # Active-run deduplication and failure backoff below still apply.[0m
2026-11-14T20:50:19.5819025Z [36;1m  # Failure-triggered evaluation must not create an immediate retry[0m
2026-11-14T20:50:19.5819501Z [36;1m  # cycle. Back off failed/cancelled free producers from completion;[0m
2026-11-14T20:50:19.5820315Z [36;1m  failure_backoff_minutes=5[0m
2026-11-14T20:50:19.5820724Z [36;1m  if [ "$workflow" = nba-new-ai-all-markets.yml ]; then failure_backoff_minutes=15; fi[0m
2026-11-14T20:50:19.5822759Z [36;1m  # request failed: avoid hammering a denied public endpoint.[0m
2026-11-14T20:50:19.5823190Z [36;1m  # Failed free runs may retry sooner than successful runs, but not[0m
2026-11-14T20:50:19.5825446Z [36;1m       --argjson failed_cutoff "$(($(date -u +%s) - failure_backoff_minutes * 60))" \[0m
2026-11-14T20:50:19.5828624Z [36;1m         (.updatedAt | fromdateiso8601) >= $failed_cutoff)[0m
2026-11-14T20:50:19.5829675Z [36;1m    echo "Skipping $workflow: active, successful cooldown, or failure backoff (paid calls hard-capped)"[0m
2026-11-14T20:50:20.7371610Z Skipping nba-prizepicks-full-slate.yml: active, successful cooldown, or failure backoff (paid calls hard-capped)
2026-11-14T20:50:20.7411294Z ##[group]Run set -euo pipefail
2026-11-14T20:50:20.7411639Z [36;1mset -euo pipefail[0m
2026-11-14T20:50:20.7412535Z [36;1mtitle="Automated incident: NBA production readiness degraded"[0m
2026-11-14T20:50:20.7414197Z [36;1m  echo "::warning::GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary."[0m
2026-11-14T20:50:20.7424404Z [36;1m  echo "### Failing required components"[0m
2026-11-14T20:50:20.7428041Z [36;1m  echo "Do not label live picks READY until the fail-closed readiness gate passes."[0m
2026-11-14T20:50:21.1133580Z ##[warning]GitHub Issues disabled: production incident will be retained in committed readiness JSON and workflow summary.
2026-11-14T20:50:21.1223650Z   if-no-files-found: error
2026-11-14T20:50:21.3039976Z (node:2975) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:50:21.3040981Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:50:21.7309448Z (node:2975) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:50:22.4469351Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T20:50:22.4617128Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T20:50:22.4619057Z ##[error]Process completed with exit code 1.
2026-11-14T20:50:22.7531591Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## verify — run 43639491825, job 132583615466

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639491825/job/132583615466

```text
2026-11-14T20:49:11.6958364Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:49:16.2251950Z (node:2484) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:49:16.2255459Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:49:16.3954274Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:49:16.4027171Z ##[error]Process completed with exit code 2.
2026-11-14T20:49:16.4148317Z ##[group]Run set -euo pipefail
2026-11-14T20:49:16.4149775Z [36;1mset -euo pipefail[0m
2026-11-14T20:49:16.9861334Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T20:49:18.2512899Z ##[error]Process completed with exit code 2.
2026-11-14T20:49:18.2571319Z ##[group]Run echo "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"
2026-11-14T20:49:18.2572206Z [36;1mecho "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"[0m
2026-11-14T20:49:18.2723853Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T20:49:18.2725650Z ##[error]Process completed with exit code 1.
2026-11-14T20:49:18.5576585Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## source-readiness — run 43639445409, job 132583557515

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639445409/job/132583557515

```text
2026-11-14T20:48:59.7364385Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:49:04.3655857Z (node:2462) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:49:04.3656990Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:49:04.7413560Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T20:49:04.715909+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage"
2026-11-14T20:49:04.7529419Z ##[error]Process completed with exit code 1.
2026-11-14T20:49:04.7607329Z ##[group]Run set -euo pipefail
2026-11-14T20:49:04.7607714Z [36;1mset -euo pipefail[0m
2026-11-14T20:49:04.7612198Z [36;1m  python -c "import json; r=json.load(open('docs/pregame_lifecycle_readiness.json')); assert r.get('status') in ('READY','NOT_READY')"[0m
2026-11-14T20:49:06.1347128Z NEXT NBA SLATE PREFLIGHT: {"generated_at": "2026-11-14T20:49:06.109468+00:00", "status": "NOT_READY", "target_date_eastern": "2026-11-15", "games": [{"game": "Indiana Pacers @ Philadelphia 76ers", "start": "2026-11-15T18:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 92, "status": "ONLY_AI"}, {"game": "Los Angeles Lakers @ Phoenix Suns", "start": "2026-11-15T21:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 108, "status": "ONLY_AI"}, {"game": "Charlotte Hornets @ LA Clippers", "start": "2026-11-15T21:30:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "San Antonio Spurs @ Utah Jazz", "start": "2026-11-15T22:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Dallas Mavericks @ Boston Celtics", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 104, "status": "ONLY_AI"}, {"game": "New York Knicks @ Toronto Raptors", "start": "2026-11-15T23:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 100, "status": "ONLY_AI"}, {"game": "Houston Rockets @ Washington Wizards", "start": "2026-11-16T00:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Atlanta Hawks @ Milwaukee Bucks", "start": "2026-11-16T01:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}, {"game": "Oklahoma City Thunder @ Sacramento Kings", "start": "2026-11-16T02:00:00+00:00", "captured_line_markets": 0, "captured_ai_forecasts": 96, "status": "ONLY_AI"}], "counts": {"scheduled": 9, "games_with_saved_quotes": 0, "games_with_saved_ai": 9, "saved_line_markets": 0, "saved_ai_forecasts": 896, "coverage"
2026-11-14T20:49:07.4683664Z [36;1mecho "::error::NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json"[0m
2026-11-14T20:49:07.5014603Z ##[error]NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json
2026-11-14T20:49:07.5017332Z ##[error]Process completed with exit code 1.
2026-11-14T20:49:07.8007380Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

## heartbeat — run 43639445400, job 132583463215

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43639445400/job/132583463215

```text
2026-11-14T20:48:40.2109779Z hint: to use in all of your new repositories, which will suppress this warning,
2026-11-14T20:48:45.1167518Z (node:2373) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:48:45.1168628Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:48:46.8245699Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T20:48:48.0688903Z {"checked_at": "2026-11-14T20:48:46.884566+00:00", "recoveries": [{"workflow": "nba-new-ai-all-markets.yml", "status": "SKIPPED", "reason": "ACTIVE_RECENT_SUCCESS_OR_FAILURE_BACKOFF"}], "status": "COMPLETE", "note": "Dispatch is not repair verification; health failures remain visible until deployed checks pass."}
2026-11-14T20:48:49.2187590Z (node:2403) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
2026-11-14T20:48:49.2188441Z (Use `node --trace-deprecation ...` to show where the warning was created)
2026-11-14T20:48:49.6521541Z (node:2403) [DEP0169] DeprecationWarning: `url.parse()` behavior is not standardized and prone to errors that have security implications. Use the WHATWG URL API instead. CVEs are not issued for `url.parse()` vulnerabilities.
2026-11-14T20:48:50.4223586Z [36;1m  echo "- **FAIL** Heartbeat report missing; inspect failed workflow and artifact." >> "$GITHUB_STEP_SUMMARY"[0m
2026-11-14T20:48:50.4412014Z ##[group]Run set -euo pipefail
2026-11-14T20:48:50.4412362Z [36;1mset -euo pipefail[0m
2026-11-14T20:48:50.4415154Z [36;1m  echo "::warning::GitHub Issues disabled or unavailable; alert evidence remains in the run summary and artifact."[0m
2026-11-14T20:48:50.4416390Z [36;1mgh label create pipeline-alert --color B60205 --description "Dame's Picks pipeline failure" 2>/dev/null || true[0m
2026-11-14T20:48:50.4418131Z [36;1m  title="[pipeline] $stage failing"[0m
2026-11-14T20:48:50.4419724Z [36;1m  if [ "$status" = FAIL ] && [ -z "$issue" ]; then[0m
2026-11-14T20:48:50.8125535Z ##[warning]GitHub Issues disabled or unavailable; alert evidence remains in the run summary and artifact.
2026-11-14T20:48:50.8247808Z ##[error]Process completed with exit code 1.
2026-11-14T20:48:51.1072490Z ##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@11d5960a326750d5838078e36cf38b85af677262, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```


## Post-merge failures and recovery

- [43642046196](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642046196) — Refresh free native NBA PrizePicks standard lines; job 132591538351; steps: Fetch free public standard NBA quotes (no paid fallback)
- [43642046292](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642046292) — Check funded independent PrizePicks API key and current quota; job 132591538693; steps: Publish quota-only status without storing offers or API key
- [43642046105](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642046105) — Verify tonight NBA frozen lines predictions and grades; job 132591537870; steps: Publish audit even if missing frozen games, Fail visibly if genuine source lines lack frozen models
- [43642046200](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642046200) — Publish trained NBA AI props for every available game; job 132591605762; steps: Confirm actual current market coverage and quote freshness
- [43642046265](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642046265) — Unified Dame's Picks NBA + NFL integrity; job 132591538320; steps: Publish both-sport integrity report without losing failures, Fail if either sport or unified entry point is degraded
- [43642044304](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642044304) — Cross-domain Sports-Bot reliability audit (no provider credits); job 132591533190; steps: Check preserved standard NFL grades, source readiness, captures and live data
- [43642044402](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642044402) — Automatically lock verified NBA pretip lines with saved baseline AI; job 132591533411; steps: Preserve only authenticated baseline pretip joins
- [43642044555](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642044555) — Grade immutable standard-line AI research receipts (credit free); job 132591534071; steps: Score saved research without querying sportsbooks
- [43642044560](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642044560) — Inspect PrizePicks compact field shape once; job 132591534169; steps: Save public-safe field schema
- [43642044450](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642044450) — NBA full-game lifecycle and next-slate readiness gate; job 132591930653; steps: Block green readiness when the next slate is missing saved sources
- [43642044508](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642044508) — Dame's Picks unified NBA + NFL app release gate; job 132591533985; steps: Recompute and publish real combined release gate, even when degraded
- [43642044449](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43642044449) — Phase 1 end-to-end eight-game reliability check; job 132591533886; steps: Audit real committed snapshots (no sportsbook credits)

Free baseline/research publisher retries succeeded; paid diagnostics were not retried. PR471 final CI requires maintainer approval.

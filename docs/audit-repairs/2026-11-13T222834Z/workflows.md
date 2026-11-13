# Workflow audit evidence

All 175 current workflow definitions received static validation. Latest observed runs are a sample, not exhaustive history. A skipped main-only deploy job on a PR is expected. Active runs are not classified stuck solely from being active. 121 per-workflow history requests were blocked; exact exceptions are in workflow-history.json.gz.

| Workflow definition | Latest observed run | Event/status | History request | Static flags |
|---|---|---|---|---|
| `.github/workflows/assist-v2-research.yml` | [43124017754](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43124017754) | pull_request / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/assist-v2-shadow.yml` | [43510334950](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43510334950) | schedule / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/audit-ai-forecast-coverage.yml` | [43434321144](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43434321144) | schedule / success | retrieved | none |
| `.github/workflows/authoritative-nba-grading-reconciliation.yml` | [43522118463](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522118463) | schedule / success | retrieved | none |
| `.github/workflows/confidence-readiness-research.yml` | [43507852946](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43507852946) | schedule / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/cross-domain-reliability-audit.yml` | [43521636423](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521636423) | schedule / failure | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/dames-picks-app-release-gate.yml` | [43521415871](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521415871) | schedule / failure | retrieved | none |
| `.github/workflows/dames-picks-recovery-regressions.yml` | [43483190097](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43483190097) | pull_request / success | retrieved | PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/dames-picks-version-e.yml` | [43522674353](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674353) | push / success | retrieved | none |
| `.github/workflows/dashboard-ui-check.yml` | [43464346034](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43464346034) | push / success | retrieved | PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/dunkapi-import-one-game.yml` | [42150222869](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42150222869) | workflow_dispatch / success | retrieved | none |
| `.github/workflows/dunkapi-probe.yml` | [42148521570](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42148521570) | workflow_dispatch / success | retrieved | none |
| `.github/workflows/end_to_end_readiness.yml` | [43519738145](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519738145) | schedule / failure | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/espn-live-json-resilience.yml` | [42751765780](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42751765780) | push / success | retrieved | none |
| `.github/workflows/external_stats_snapshot_tests.yml` | [42700717936](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42700717936) | push / success | retrieved | PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/freeze_baseline_pregame_quotes.yml` | [43521615776](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521615776) | schedule / success | retrieved | none |
| `.github/workflows/full-repository-audit.yml` | [43508627882](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43508627882) | schedule / failure | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/grade-standard-quote-ai-research.yml` | [43490978214](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43490978214) | schedule / success | retrieved | none |
| `.github/workflows/grade_automatic_baseline_join.yml` | [43522838574](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522838574) | schedule / success | retrieved | none |
| `.github/workflows/grade_frozen_ai_forecasts.yml` | [43518336348](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518336348) | schedule / success | retrieved | none |
| `.github/workflows/grade_frozen_baseline_join.yml` | [43518641204](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518641204) | schedule / success | retrieved | none |
| `.github/workflows/hide-tipped-ai-props-tests.yml` | [43522321158](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522321158) | pull_request / success | retrieved | none |
| `.github/workflows/independent_nba_player_boxscores.yml` | [43521470787](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521470787) | push / success | retrieved | none |
| `.github/workflows/independent_scoreboard_refresh.yml` | [43521691625](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521691625) | schedule / success | retrieved | none |
| `.github/workflows/inspect-prizepicks-compact.yml` | [42434907890](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42434907890) | push / success | retrieved | none |
| `.github/workflows/live-night-integration.yml` | [43382781046](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43382781046) | schedule / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/live-site-e2e.yml` | [43522865746](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522865746) | workflow_run / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/model-disagreement-research.yml` | [42433382451](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42433382451) | pull_request / success | retrieved | none |
| `.github/workflows/nba-20k-stress-research.yml` | [42433382466](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42433382466) | pull_request / success | retrieved | none |
| `.github/workflows/nba-ai-comparisons.yml` | [43514736498](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43514736498) | schedule / failure | retrieved | none |
| `.github/workflows/nba-ai-record.yml` | [43497215291](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43497215291) | schedule / success | retrieved | none |
| `.github/workflows/nba-assist-night-comparison.yml` | [42467613197](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42467613197) | push / success | retrieved | none |
| `.github/workflows/nba-audit-real-props.yml` | [42151179967](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42151179967) | workflow_dispatch / success | retrieved | none |
| `.github/workflows/nba-backtest-provisional.yml` | [42146604801](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42146604801) | workflow_dispatch / success | retrieved | none |
| `.github/workflows/nba-backtest-real-market.yml` | No fresh run in retrieved sample | unknown / not observed | retrieved | none |
| `.github/workflows/nba-build-dataset.yml` | [42145056118](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42145056118) | workflow_dispatch / success | retrieved | none |
| `.github/workflows/nba-consensus-test.yml` | [43522674323](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674323) | push / success | retrieved | PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-cross-market-coherence.yml` | [43442770395](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43442770395) | schedule / success | retrieved | none |
| `.github/workflows/nba-current-form.yml` | [43448063907](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43448063907) | schedule / success | retrieved | none |
| `.github/workflows/nba-defender-rotation.yml` | [42161289144](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42161289144) | workflow_dispatch / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-defender-v3-research.yml` | [43124311827](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43124311827) | push / success | retrieved | none |
| `.github/workflows/nba-defense-challenger.yml` | [42158111775](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42158111775) | workflow_dispatch / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-durable-research-tests.yml` | [43124017609](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43124017609) | pull_request / success | retrieved | none |
| `.github/workflows/nba-expanded-matchup-holdout.yml` | [42700324167](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42700324167) | pull_request / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-extreme-miss-forensics.yml` | [42689017571](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42689017571) | pull_request / success | retrieved | none |
| `.github/workflows/nba-fast-injury-reprojection.yml` | [43518694067](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518694067) | schedule / success | retrieved | none |
| `.github/workflows/nba-free-official-injury-watch.yml` | [43520617479](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43520617479) | schedule / success | retrieved | none |
| `.github/workflows/nba-full-game-lifecycle.yml` | [43514673659](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43514673659) | schedule / failure | retrieved | none |
| `.github/workflows/nba-grading-overdue.yml` | [43417722537](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43417722537) | schedule / success | retrieved | none |
| `.github/workflows/nba-historical-minutes.yml` | [43124311971](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43124311971) | push / success | retrieved | none |
| `.github/workflows/nba-hoopr-schedule-probe.yml` | [42532035339](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42532035339) | push / success | retrieved | none |
| `.github/workflows/nba-injury-ai-recovery.yml` | [43518630292](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518630292) | schedule / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-kaggle-file-list.yml` | [42527282139](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42527282139) | push / success | retrieved | none |
| `.github/workflows/nba-kaggle-range-inspect.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-kaggle-schema-audit.yml` | [42527186054](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42527186054) | push / success | retrieved | none |
| `.github/workflows/nba-kaggle-source-audit.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-lagged-matchup-training.yml` | [42710056482](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/42710056482) | pull_request / success | retrieved | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-live-lagged-challenger.yml` | [43508245829](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43508245829) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-live-matchup-tracker-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-live-research-checkpoints.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-live-tracker-backup.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-live-tracker-external-verification.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-live-tracker-v2-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-main-card-coverage.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-market-refresh.yml` | [43514627760](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43514627760) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-minutes-v3-opportunity-v2.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-model-readiness.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-moneylines.yml` | [43517073207](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43517073207) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-new-ai-all-markets.yml` | [43521731476](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521731476) | workflow_dispatch / success | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-new-ai-multimarket-grade.yml` | [43518385557](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518385557) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-new-model-points-grading.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-no-line-daily-projections.yml` | [43514592420](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43514592420) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-odds-budget-coverage-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-odds-current-balance.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-offensive-involvement-holdout.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-opportunity-shadow-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-position-defense.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-postgame-settlement.yml` | [43511895841](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43511895841) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-pregame-ai-archive.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-prizepicks-ai-board.yml` | [43521725404](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521725404) | workflow_dispatch / success | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE, PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-prizepicks-ai-offline-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-prizepicks-ai-research.yml` | [43521735112](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521735112) | workflow_dispatch / success | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-prizepicks-current-balance.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-prizepicks-full-slate.yml` | [43521653591](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521653591) | workflow_dispatch / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-prizepicks-research-ledger.yml` | [43517050755](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43517050755) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-prizepicks-rest-setup.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-prizepicks-sample-backtest-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-prizepicks-site-publish.yml` | [43521690054](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521690054) | workflow_dispatch / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-prizepicks-topup-verification.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-projection-upgrade-research.yml` | [43519111992](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519111992) | unknown / skipped | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-props.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-publish-research.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-published-pick-settlement.yml` | [43514317292](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43514317292) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-real-results.yml` | [43521131098](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521131098) | push / success | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-rebound-shadow-validation.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | PRODUCTION_UNIT_TEST_GATE |
| `.github/workflows/nba-research-prospective-capture-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-research-storage-integrity.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-schedule.yml` | [43521411746](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521411746) | schedule / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-scores.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-season-horizon-audit.yml` | [43508537315](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43508537315) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-shooting-efficiency-v1.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-slate-coverage-health.yml` | [43517279320](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43517279320) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-slate-resilience-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-tonight-capture-gradeability.yml` | [43523310472](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43523310472) | schedule / failure | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-tracking-coverage.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-tracking-opportunities-validation.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-tracking-provider-access.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-train-provisional.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-trained-ai-board.yml` | [43519076571](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519076571) | unknown / failure | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-ui-integrity.yml` | [43522674433](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674433) | push / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nba-underprojection-research.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nfl-boxscores-publish.yml` | [43518342936](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518342936) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nfl-live-tracker.yml` | [43518102838](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518102838) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nfl-live-ui-qa.yml` | [43522674319](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674319) | push / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nfl-pick-grading.yml` | [43523003703](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43523003703) | schedule / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nfl-private-sync.yml` | [43521624095](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521624095) | schedule / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nfl-reconciliation-ci.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nfl-schedule-publish.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nfl-ui-smoke.yml` | [43522674544](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674544) | push / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nightly_grade_date_audit.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/nightly_settlement_health.yml` | [43519385976](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519385976) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/official_nba_fixture_reconciliation.yml` | [43511631117](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43511631117) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/opponent_simulation_tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/pages-controlled.yml` | [43523354605](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43523354605) | schedule / in_progress | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/pbpstats-connectivity-probe.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/pbpstats-current-season-probe.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/pbpstats-onoff-coverage-probe.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/pbpstats-wowy-validation.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/phase1-e2e-grading.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/phase1-free-recovery.yml` | [43515414700](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43515414700) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/phase1-live-service-replit.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/phase1_board_readiness.yml` | [43505899020](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43505899020) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/phase1_dashboard_scoreboard.yml` | [43522674590](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674590) | push / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/phase1_data_integrity.yml` | [43515158817](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43515158817) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/phase1_feed_health.yml` | [43522621915](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522621915) | schedule / failure | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/phase1_real_pp_join.yml` | [43522674280](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674280) | push / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/pipeline-contracts.yml` | [43522321326](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522321326) | pull_request / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/pipeline-heartbeat.yml` | [43521783568](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521783568) | workflow_run / failure | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/pregame_coverage_watchdog.yml` | [43518096986](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518096986) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/prizepicks-full-board-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/prizepicks_nba_collector.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/production_readiness.yml` | [43523353756](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43523353756) | workflow_run / in_progress | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/publish_live_pp_ai_join.yml` | [43521738090](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521738090) | workflow_dispatch / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/readiness.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/refresh_ai_forecast_coverage_audit.yml` | [43518804263](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43518804263) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/reliability_guardrails.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-current-position-defense.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-defensive-rating-source.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-matchup-asof-audit.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-matchup-hit-estimate.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-matchup-prospective-calibration.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-matchup-shadow-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-official-defense-history.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-pregame-evidence.yml` | [43516040679](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43516040679) | unknown / success | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/research-safety-ci.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/sanity-shadow-grading-research.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/sanity-shadow-v1-research.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/test_final_transition_grade_trigger.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: HTTP Error 403: Forbidden | none |
| `.github/workflows/test_hoopr_schedule_integrity.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/test_pregame_line_archive.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/underdog-nba-injury-watch.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/underdog-xurl-connection-test.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/unified-dames-picks-readiness.yml` | [43523353543](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43523353543) | workflow_run / in_progress | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/unified-reliability-research.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verified-research-no-play-tests.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify-dames-picks-public.yml` | [43521569177](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43521569177) | schedule / success | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify-live-tracker-espn.yml` | [43522321127](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522321127) | pull_request / success | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify-prizepicks-credits.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify-public-board-diagnostics.yml` | [43522674344](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674344) | push / success | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify-public-dames-release.yml` | [43522675257](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522675257) | push / success | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify-public-matchup-preview.yml` | [43519432233](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43519432233) | unknown / success | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify_browser_dashboard.yml` | [43522674526](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674526) | push / success | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify_live_pregame_line_browser.yml` | No fresh run in retrieved sample | unknown / not observed | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify_public_dashboard.yml` | [43522215640](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522215640) | schedule / success | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |
| `.github/workflows/verify_unified_dames_browser.yml` | [43522674613](https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43522674613) | push / success | BLOCKED: <urlopen error Tunnel connection failed: 403 Forbidden> | none |

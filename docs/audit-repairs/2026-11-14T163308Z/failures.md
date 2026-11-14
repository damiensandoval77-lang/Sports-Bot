# Failed workflow jobs inspected

## 43615472585 — Phase 1 end-to-end eight-game reliability check

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43615472585

Job 132509449606: verify

```text
2026-11-14T16:25:05.1800899Z   "status": "DEGRADED",
2026-11-14T16:25:05.1809130Z   "failures": [
2026-11-14T16:25:05.1853619Z ##[error]Process completed with exit code 1.
```

## 43614472750 — Cross-domain Sports-Bot reliability audit (no provider credits)

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43614472750

Job 132506403711: audit

```text
2026-11-14T16:14:10.2770869Z       "detail": "0 pending frozen standard-line picks"
2026-11-14T16:14:10.2771759Z       "code": "ALTERNATIVE_TIERS_EXCLUDED",
2026-11-14T16:14:10.2772074Z       "detail": "932 historical alternative-tier grades and 4 pending alternative-tier rows excluded from official standard results"
2026-11-14T16:14:10.2772862Z       "code": "NEXT_14_DAYS_ACCOUNTED",
2026-11-14T16:14:10.2773069Z       "detail": "1200 fixed released fixtures saved and next two days reconciled"
2026-11-14T16:14:10.2774114Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T16:14:10.2774307Z       "detail": "status=DEGRADED; check published readiness blockers"
2026-11-14T16:14:10.2774989Z       "code": "MATCHED",
2026-11-14T16:14:10.2775128Z       "detail": "5 verified matched games"
2026-11-14T16:14:10.2775790Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T16:14:10.2776124Z       "detail": "22 exact standard prices lack primary frozen models; 17 have independently preserved research receipts, 5 have no AI receipt"
2026-11-14T16:14:10.2776939Z       "code": "RECEIPTS_RETAINED",
2026-11-14T16:14:10.2777146Z       "detail": "2175 separate historical research receipts (not official grades)"
2026-11-14T16:14:10.2778015Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T16:14:10.2778178Z       "detail": "ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR"
2026-11-14T16:14:10.2778827Z       "code": "COMPLETE_SOURCE",
2026-11-14T16:14:10.2778991Z       "detail": "Provider board reports complete coverage"
2026-11-14T16:14:10.2779897Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T16:14:10.2780079Z       "detail": "0 active matchups at last published snapshot"
2026-11-14T16:14:10.2832963Z ##[error]Process completed with exit code 1.
```

## 43614437501 — Dame's Picks unified NBA + NFL app release gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43614437501

Job 132506293564: verify

```text
2026-11-14T16:13:46.6641921Z [36;1mecho "::error::Could not publish merged app release verification"[0m
2026-11-14T16:13:48.9563210Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T16:13:49.0458925Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T16:13:49.0766638Z DAMES_PICKS_RELEASE_GATE {"checked_at": "2026-11-14T16:13:49.075535+00:00", "status": "DEGRADED", "checks_passing": false, "release_certified": false, "healthy_streak_started_at": null, "healthy_streak_hours": 0.0, "required_consecutive_hours": 72, "blocking_checks": ["unified_artifacts", "nba_production", "nba_capture"], "checks": {"unified_artifacts": {"state": "DEGRADED", "issues": ["UNIFIED_APP_ARTIFACTS_NOT_READY", "NBA_OR_NFL_ARTIFACTS_NOT_READY"]}, "public_unified_browser": {"state": "READY", "issues": []}, "nba_production": {"state": "DEGRADED", "issues": ["NBA_PRODUCTION_NOT_READY", "NBA_FAILED_CURRENT_PRIMARY_MODEL_COVERAGE"]}, "nba_capture": {"state": "DEGRADED", "issues": ["PRIMARY_STANDARD_COVERAGE_INCOMPLETE"]}, "nba_grading": {"state": "READY", "issues": []}, "published_pick_settlement": {"state": "READY", "issues": []}, "nfl_grading": {"state": "READY", "issues": []}}, "scope": "UNIFIED_DAMES_PICKS_NBA_NFL_RELEASE_GATE", "note": "72h sustained clean artifacts and observed public browser, pretip captures, frozen standard-only grading and current source gates; this does not prove predictive accuracy or zero downtime."}
2026-11-14T16:13:52.0425743Z ##[error]Process completed with exit code 2.
```

## 43614155485 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43614155485

Job 132505431592: verify-readiness

```text
2026-11-14T16:12:03.0384742Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T16:12:03.0441970Z ##[error]Process completed with exit code 2.
2026-11-14T16:12:04.3396873Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T16:12:09.9607055Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T16:12:09.9713387Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T16:12:09.9715591Z ##[error]Process completed with exit code 1.
```

## 43613238445 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43613238445

Job 132502808359: verify-readiness

```text
2026-11-14T16:02:45.8890100Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T16:02:45.8972197Z ##[error]Process completed with exit code 2.
2026-11-14T16:02:46.4976020Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T16:02:49.3426029Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T16:02:49.3565812Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T16:02:49.3567770Z ##[error]Process completed with exit code 1.
```

## 43613132415 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43613132415

Job 132502343809: verify-readiness

```text
2026-11-14T16:01:11.2476726Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T16:01:11.2539485Z ##[error]Process completed with exit code 2.
2026-11-14T16:01:13.3197724Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T16:01:16.6969340Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T16:01:16.7094213Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T16:01:16.7096555Z ##[error]Process completed with exit code 1.
```

## 43612379957 — Phase 1 end-to-end eight-game reliability check

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43612379957

Job 132499994714: verify

```text
2026-11-14T15:51:12.0305025Z   "status": "DEGRADED",
2026-11-14T15:51:12.0310678Z   "failures": [
2026-11-14T15:51:12.0360853Z ##[error]Process completed with exit code 1.
```

## 43612088809 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43612088809

Job 132499117161: verify-readiness

```text
2026-11-14T15:49:12.8800748Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T15:49:12.8874195Z ##[error]Process completed with exit code 2.
2026-11-14T15:49:14.7250063Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T15:49:18.0000932Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T15:49:18.0165429Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T15:49:18.0167781Z ##[error]Process completed with exit code 1.
```

## 43612074196 — Phase 1 feed health audit

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43612074196

Job 132499071865: feed-health

```text
2026-11-14T15:47:46.3019691Z       "detail": "0 pending frozen standard-line picks"
2026-11-14T15:47:46.3021102Z       "code": "ALTERNATIVE_TIERS_EXCLUDED",
2026-11-14T15:47:46.3021574Z       "detail": "932 historical alternative-tier grades and 4 pending alternative-tier rows excluded from official standard results"
2026-11-14T15:47:46.3022720Z       "code": "NEXT_14_DAYS_ACCOUNTED",
2026-11-14T15:47:46.3023017Z       "detail": "1200 fixed released fixtures saved and next two days reconciled"
2026-11-14T15:47:46.3024066Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T15:47:46.3024347Z       "detail": "status=DEGRADED; check published readiness blockers"
2026-11-14T15:47:46.3025396Z       "code": "MATCHED",
2026-11-14T15:47:46.3025597Z       "detail": "5 verified matched games"
2026-11-14T15:47:46.3026530Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T15:47:46.3027183Z       "detail": "22 exact standard prices lack primary frozen models; 17 have independently preserved research receipts, 5 have no AI receipt"
2026-11-14T15:47:46.3028526Z       "code": "RECEIPTS_RETAINED",
2026-11-14T15:47:46.3028823Z       "detail": "2175 separate historical research receipts (not official grades)"
2026-11-14T15:47:46.3029795Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T15:47:46.3030026Z       "detail": "ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR"
2026-11-14T15:47:46.3030972Z       "code": "COMPLETE_SOURCE",
2026-11-14T15:47:46.3031218Z       "detail": "Provider board reports complete coverage"
2026-11-14T15:47:46.3032179Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T15:47:46.3032440Z       "detail": "0 active matchups at last published snapshot"
2026-11-14T15:47:46.3076806Z ##[error]Process completed with exit code 1.
```

## 43612052763 — Unified Dame's Picks NBA + NFL integrity

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43612052763

Job 132499007197: verify

```text
2026-11-14T15:47:35.8111403Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T15:47:35.8175517Z ##[error]Process completed with exit code 2.
2026-11-14T15:47:37.1817026Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T15:47:38.5740193Z ##[error]Process completed with exit code 2.
2026-11-14T15:47:38.5773525Z ##[group]Run echo "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"
2026-11-14T15:47:38.5774158Z [36;1mecho "::error::Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json"[0m
2026-11-14T15:47:38.5888071Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T15:47:38.5889446Z ##[error]Process completed with exit code 1.
```

## 43611699082 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43611699082

Job 132497936871: verify-readiness

```text
2026-11-14T15:44:49.7677252Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T15:44:49.7735610Z ##[error]Process completed with exit code 2.
2026-11-14T15:44:50.8845595Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T15:44:53.1697408Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T15:44:53.1820605Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T15:44:53.1822173Z ##[error]Process completed with exit code 1.
```

## 43610542489 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43610542489

Job 132494441211: verify-readiness

```text
2026-11-14T15:31:57.5530040Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T15:31:57.5596360Z ##[error]Process completed with exit code 2.
2026-11-14T15:31:59.2382664Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T15:32:02.9783474Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T15:32:02.9930418Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T15:32:02.9932598Z ##[error]Process completed with exit code 1.
```

## 43609998760 — Verify tonight NBA frozen lines predictions and grades

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43609998760

Job 132492755790: audit

```text
2026-11-14T15:24:29.2706825Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T15:24:29.4473383Z ##[error]Process completed with exit code 1.
2026-11-14T15:24:29.4528796Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T15:24:30.7348834Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T15:24:32.1460309Z ##[error]Process completed with exit code 1.
2026-11-14T15:24:32.1493080Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T15:24:32.1493934Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T15:24:32.1606523Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T15:24:32.1607989Z ##[error]Process completed with exit code 1.
```

## 43609924422 — Verify tonight NBA frozen lines predictions and grades

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43609924422

Job 132492501383: audit

```text
2026-11-14T15:23:37.7468847Z PRIMARY STANDARD LINE RECOVERY: 43 {'MOVED_ORIGINAL_STANDARD_THRESHOLD': 18, 'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 25}
2026-11-14T15:23:37.9666480Z ##[error]Process completed with exit code 1.
2026-11-14T15:23:37.9735715Z [36;1mecho "::error::Could not publish per-game capture health after retries"[0m
2026-11-14T15:23:39.1686763Z PRIMARY STANDARD LINE RECOVERY: 43 {'MOVED_ORIGINAL_STANDARD_THRESHOLD': 18, 'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 25}
2026-11-14T15:23:40.7021044Z ##[error]Process completed with exit code 1.
2026-11-14T15:23:40.7066277Z ##[group]Run echo "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"
2026-11-14T15:23:40.7067470Z [36;1mecho "::error::CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json"[0m
2026-11-14T15:23:40.7207420Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T15:23:40.7209409Z ##[error]Process completed with exit code 1.
```

## 43609865644 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43609865644

Job 132492343945: verify-readiness

```text
2026-11-14T15:24:20.3946441Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T15:24:20.4019461Z ##[error]Process completed with exit code 2.
2026-11-14T15:24:21.4735272Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T15:24:24.3566678Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T15:24:24.3736546Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T15:24:24.3739008Z ##[error]Process completed with exit code 1.
```

## 43609732407 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43609732407

Job 132491906215: verify-readiness

```text
2026-11-14T15:22:45.5000899Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T15:22:45.5072681Z ##[error]Process completed with exit code 2.
2026-11-14T15:22:46.7365503Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T15:22:52.2164205Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T15:22:52.2291090Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T15:22:52.2292648Z ##[error]Process completed with exit code 1.
```

## 43609183288 — Cross-domain Sports-Bot reliability audit (no provider credits)

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43609183288

Job 132490247339: audit

```text
2026-11-14T15:15:32.7194931Z       "detail": "0 pending frozen standard-line picks"
2026-11-14T15:15:32.7196704Z       "code": "ALTERNATIVE_TIERS_EXCLUDED",
2026-11-14T15:15:32.7197529Z       "detail": "932 historical alternative-tier grades and 4 pending alternative-tier rows excluded from official standard results"
2026-11-14T15:15:32.7199728Z       "code": "NEXT_14_DAYS_ACCOUNTED",
2026-11-14T15:15:32.7200275Z       "detail": "1200 fixed released fixtures saved and next two days reconciled"
2026-11-14T15:15:32.7202364Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T15:15:32.7202851Z       "detail": "status=DEGRADED; check published readiness blockers"
2026-11-14T15:15:32.7204819Z       "code": "MATCHED",
2026-11-14T15:15:32.7205203Z       "detail": "5 verified matched games"
2026-11-14T15:15:32.7207172Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T15:15:32.7208042Z       "detail": "21 exact standard prices lack primary frozen models; 16 have independently preserved research receipts, 5 have no AI receipt"
2026-11-14T15:15:32.7210100Z       "code": "RECEIPTS_RETAINED",
2026-11-14T15:15:32.7210642Z       "detail": "2153 separate historical research receipts (not official grades)"
2026-11-14T15:15:32.7212670Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T15:15:32.7213074Z       "detail": "ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR"
2026-11-14T15:15:32.7214711Z       "code": "COMPLETE_SOURCE",
2026-11-14T15:15:32.7215127Z       "detail": "Provider board reports complete coverage"
2026-11-14T15:15:32.7216928Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T15:15:32.7217373Z       "detail": "0 active matchups at last published snapshot"
2026-11-14T15:15:32.7262282Z ##[error]Process completed with exit code 1.
```

## 43609133466 — Dame's Picks unified NBA + NFL app release gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43609133466

Job 132490099290: verify

```text
2026-11-14T15:15:02.0620687Z [36;1mecho "::error::Could not publish merged app release verification"[0m
2026-11-14T15:15:04.0903596Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T15:15:04.1822483Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T15:15:04.2133209Z DAMES_PICKS_RELEASE_GATE {"checked_at": "2026-11-14T15:15:04.212518+00:00", "status": "DEGRADED", "checks_passing": false, "release_certified": false, "healthy_streak_started_at": null, "healthy_streak_hours": 0.0, "required_consecutive_hours": 72, "blocking_checks": ["unified_artifacts", "nba_production", "nba_capture"], "checks": {"unified_artifacts": {"state": "DEGRADED", "issues": ["UNIFIED_APP_ARTIFACTS_NOT_READY", "NBA_OR_NFL_ARTIFACTS_NOT_READY"]}, "public_unified_browser": {"state": "READY", "issues": []}, "nba_production": {"state": "DEGRADED", "issues": ["NBA_PRODUCTION_NOT_READY", "NBA_FAILED_PRIZEPICKS_LINES", "NBA_FAILED_CURRENT_PRIMARY_MODEL_COVERAGE"]}, "nba_capture": {"state": "DEGRADED", "issues": ["PRIMARY_STANDARD_COVERAGE_INCOMPLETE"]}, "nba_grading": {"state": "READY", "issues": []}, "published_pick_settlement": {"state": "READY", "issues": []}, "nfl_grading": {"state": "READY", "issues": []}}, "scope": "UNIFIED_DAMES_PICKS_NBA_NFL_RELEASE_GATE", "note": "72h sustained clean artifacts and observed public browser, pretip captures, frozen standard-only grading and current source gates; this does not prove predictive accuracy or zero downtime."}
2026-11-14T15:15:05.7683979Z ##[error]Process completed with exit code 2.
```

## 43608920218 — Phase 1 end-to-end eight-game reliability check

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43608920218

Job 132489418571: verify

```text
2026-11-14T15:12:38.0082785Z   "status": "DEGRADED",
2026-11-14T15:12:38.0087455Z   "failures": [
2026-11-14T15:12:38.0138586Z ##[error]Process completed with exit code 1.
```

## 43607982125 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43607982125

Job 132486639951: verify-readiness

```text
2026-11-14T15:03:46.3589310Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T15:03:46.3657841Z ##[error]Process completed with exit code 2.
2026-11-14T15:03:48.0764668Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T15:03:52.2354941Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T15:03:52.2476866Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T15:03:52.2479324Z ##[error]Process completed with exit code 1.
```

## 43607823313 — Full repository static and workflow architecture audit

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43607823313

Job 132486180434: Verify actual production health and invoke bounded free recovery

```text
2026-11-14T15:08:56.9398223Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9402134Z         "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9402579Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9409023Z         "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9409465Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9413160Z         "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9413734Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9417462Z         "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9417919Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9421811Z         "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9422243Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9425875Z         "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9426282Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9429798Z         "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9430210Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9434093Z         "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9434606Z       "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9438452Z       "PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE"
2026-11-14T15:08:56.9438853Z     "readiness_status": "DEGRADED",
2026-11-14T15:08:56.9449844Z ##[error]Process completed with exit code 1.
```

## 43607823313 — Full repository static and workflow architecture audit

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43607823313

Job 132488464082: Publish evidence and surface audit failures

```text
2026-11-14T15:09:12.9652304Z ##[error]Process completed with exit code 1.
```

## 43607214258 — NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43607214258

Job 132484333043: verify-readiness

```text
2026-11-14T14:54:56.3453387Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T14:54:56.3507946Z ##[error]Process completed with exit code 2.
2026-11-14T14:54:57.5319628Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T14:55:01.7971612Z [36;1mecho "::error::NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json"[0m
2026-11-14T14:55:01.8101135Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T14:55:01.8102724Z ##[error]Process completed with exit code 1.
```

## 43606954704 — Phase 1 feed health audit

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43606954704

Job 132483542415: feed-health

```text
2026-11-14T14:50:41.9137740Z       "detail": "0 pending frozen standard-line picks"
2026-11-14T14:50:41.9139269Z       "code": "ALTERNATIVE_TIERS_EXCLUDED",
2026-11-14T14:50:41.9139970Z       "detail": "932 historical alternative-tier grades and 4 pending alternative-tier rows excluded from official standard results"
2026-11-14T14:50:41.9141169Z       "code": "NEXT_14_DAYS_ACCOUNTED",
2026-11-14T14:50:41.9141469Z       "detail": "1200 fixed released fixtures saved and next two days reconciled"
2026-11-14T14:50:41.9142477Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T14:50:41.9142740Z       "detail": "status=DEGRADED; check published readiness blockers"
2026-11-14T14:50:41.9143714Z       "code": "MATCHED",
2026-11-14T14:50:41.9143906Z       "detail": "5 verified matched games"
2026-11-14T14:50:41.9144824Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T14:50:41.9145551Z       "detail": "21 exact standard prices lack primary frozen models; 16 have independently preserved research receipts, 5 have no AI receipt"
2026-11-14T14:50:41.9146733Z       "code": "RECEIPTS_RETAINED",
2026-11-14T14:50:41.9147027Z       "detail": "2153 separate historical research receipts (not official grades)"
2026-11-14T14:50:41.9147997Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T14:50:41.9148378Z       "detail": "ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR"
2026-11-14T14:50:41.9149419Z       "code": "COMPLETE_SOURCE",
2026-11-14T14:50:41.9149666Z       "detail": "Provider board reports complete coverage"
2026-11-14T14:50:41.9150589Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T14:50:41.9150842Z       "detail": "0 active matchups at last published snapshot"
2026-11-14T14:50:41.9204806Z ##[error]Process completed with exit code 1.
```

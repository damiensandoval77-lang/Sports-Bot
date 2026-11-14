# Failed workflow evidence

## Cross-domain Sports-Bot reliability audit (no provider credits)

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43604261179

Job 132475392300: audit

```
2026-11-14T14:19:41.3932833Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T14:19:41.3933967Z       "code": "MATCHED",
2026-11-14T14:19:41.3935008Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T14:19:41.3936430Z       "code": "RECEIPTS_RETAINED",
2026-11-14T14:19:41.3937708Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T14:19:41.3938763Z       "code": "COMPLETE_SOURCE",
2026-11-14T14:19:41.3939837Z       "code": "STALE_HEALTH_REPORT",
2026-11-14T14:19:41.3941046Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T14:19:41.3981820Z ##[error]Process completed with exit code 1.
```

## Dame's Picks unified NBA + NFL app release gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43604130783

Job 132474991289: verify

```
2026-11-14T14:18:12.8173145Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:18:12.9344426Z DAMES_PICKS_RELEASE_GATE {"checked_at": "2026-11-14T14:18:12.933662+00:00", "status": "DEGRADED", "checks_passing": false, "release_certified": false, "healthy_streak_started_at": null, "healthy_streak_hours": 0.0, "required_consecutive_hours": 72, "blocking_checks": ["unified_artifacts", "nba_production", "nba_capture"], "checks": {"unified_artifacts": {"state": "DEGRADED", "issues": ["UNIFIED_APP_ARTIFACTS_NOT_READY", "NBA_OR_NFL_ARTIFACTS_NOT_READY"]}, "public_unified_browser": {"state": "READY", "issues": []}, "
2026-11-14T14:18:14.2793074Z ##[error]Process completed with exit code 2.
```

## Phase 1 end-to-end eight-game reliability check

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43603956215

Job 132474452743: verify

```
2026-11-14T14:16:12.2819801Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43603945256

Job 132474418669: verify-readiness

```
2026-11-14T14:17:20.3408262Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:17:20.3492471Z ##[error]Process completed with exit code 2.
2026-11-14T14:17:22.0722388Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:17:27.8727874Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T14:17:27.8730418Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43603713635

Job 132473705281: verify-readiness

```
2026-11-14T14:14:34.2547616Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:14:34.2595149Z ##[error]Process completed with exit code 2.
2026-11-14T14:14:35.3535609Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:14:38.6470350Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T14:14:38.6472047Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43603367943

Job 132472801730: verify-readiness

```
2026-11-14T14:11:12.4002911Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:11:12.4056657Z ##[error]Process completed with exit code 2.
2026-11-14T14:11:13.4985890Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:11:16.3133484Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T14:11:16.3135014Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43603270123

Job 132472384151: verify-readiness

```
2026-11-14T14:09:38.9924462Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:09:38.9977742Z ##[error]Process completed with exit code 2.
2026-11-14T14:09:40.4577449Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T14:09:43.8170224Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T14:09:43.8171654Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43602416371

Job 132469826309: verify-readiness

```
2026-11-14T13:59:52.6794331Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T13:59:52.6848521Z ##[error]Process completed with exit code 2.
2026-11-14T13:59:53.9253323Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T13:59:57.0485438Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T13:59:57.0487068Z ##[error]Process completed with exit code 1.
```

## Unified Dame's Picks NBA + NFL integrity

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43602318607

Job 132469523902: verify

```
2026-11-14T13:57:21.9907683Z ##[error]Process completed with exit code 2.
2026-11-14T13:57:24.8375736Z ##[error]Process completed with exit code 2.
2026-11-14T13:57:24.8538639Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T13:57:24.8539959Z ##[error]Process completed with exit code 1.
```

## Phase 1 feed health audit

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43602317224

Job 132469518990: feed-health

```
2026-11-14T13:57:23.0449805Z       "code": "ODDS_STALE",
2026-11-14T13:57:23.0451385Z       "code": "ZERO_SLATE_COVERAGE",
2026-11-14T13:57:23.0452941Z       "code": "LIMITED_MARKETS",
2026-11-14T13:57:23.0454167Z       "code": "TRACKER_STALE",
2026-11-14T13:57:23.0503560Z ##[error]Process completed with exit code 1.
```

## Verify tonight NBA frozen lines predictions and grades

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43602019250

Job 132468607369: audit

```
2026-11-14T13:53:39.5431835Z ##[error]Process completed with exit code 1.
2026-11-14T13:53:42.7819188Z ##[error]Process completed with exit code 1.
2026-11-14T13:53:42.7979725Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T13:53:42.7981408Z ##[error]Process completed with exit code 1.
```

## Verify tonight NBA frozen lines predictions and grades

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43601954853

Job 132468411886: audit

```
2026-11-14T13:52:58.6748964Z ##[error]Process completed with exit code 1.
2026-11-14T13:53:01.3615461Z ##[error]Process completed with exit code 1.
2026-11-14T13:53:01.3715141Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T13:53:01.3716907Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43601779570

Job 132467869338: verify-readiness

```
2026-11-14T13:51:57.5842365Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T13:51:57.5910747Z ##[error]Process completed with exit code 2.
2026-11-14T13:51:59.1893234Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T13:52:03.8892706Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T13:52:03.8896046Z ##[error]Process completed with exit code 1.
```

## Live deployed Dame's Picks iPhone browser E2E

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43601322443

Job 132466487828: deployed-iphone (chromium)

```
2026-11-14T13:46:24.3562218Z ##[error]Process completed with exit code 1.
```

## Verify public Sports-Bot dashboard deployment and real JSON

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43600173422

Job 132463025858: deployed-site

```
2026-11-14T13:32:09.3546462Z ##[error]Process completed with exit code 1.
2026-11-14T13:32:12.5239909Z ##[error]Public Sports-Bot page or saved research join is not verified. See docs/deployed_dashboard_probe.json
2026-11-14T13:32:12.5242025Z ##[error]Process completed with exit code 1.
```

## Cross-domain Sports-Bot reliability audit (no provider credits)

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43599980354

Job 132462469751: audit

```
2026-11-14T13:29:17.2491265Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T13:29:17.2492906Z       "code": "MATCHED",
2026-11-14T13:29:17.2494335Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T13:29:17.2496590Z       "code": "RECEIPTS_RETAINED",
2026-11-14T13:29:17.2498634Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T13:29:17.2500138Z       "code": "COMPLETE_SOURCE",
2026-11-14T13:29:17.2501671Z       "code": "STALE_HEALTH_REPORT",
2026-11-14T13:29:17.2503162Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T13:29:17.2557927Z ##[error]Process completed with exit code 1.
```

## Dame's Picks unified NBA + NFL app release gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43599910845

Job 132462258892: verify

```
2026-11-14T13:28:27.0462785Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T13:28:27.1882762Z DAMES_PICKS_RELEASE_GATE {"checked_at": "2026-11-14T13:28:27.186957+00:00", "status": "DEGRADED", "checks_passing": false, "release_certified": false, "healthy_streak_started_at": null, "healthy_streak_hours": 0.0, "required_consecutive_hours": 72, "blocking_checks": ["unified_artifacts", "nba_production", "nba_capture"], "checks": {"unified_artifacts": {"state": "DEGRADED", "issues": ["UNIFIED_APP_ARTIFACTS_NOT_READY", "NBA_OR_NFL_ARTIFACTS_NOT_READY"]}, "public_unified_browser": {"state": "READY", "issues": []}, "
2026-11-14T13:28:28.5820970Z ##[error]Process completed with exit code 2.
```

## Phase 1 end-to-end eight-game reliability check

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43599774055

Job 132461835394: verify

```
2026-11-14T13:26:41.8141054Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43599770899

Job 132461826495: verify-readiness

```
2026-11-14T13:27:55.0166306Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T13:27:55.0239261Z ##[error]Process completed with exit code 2.
2026-11-14T13:27:56.8003001Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T13:28:00.8604759Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T13:28:00.8608028Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43599253428

Job 132460641467: verify-readiness

```
2026-11-14T13:23:13.2431648Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T13:23:13.2501333Z ##[error]Process completed with exit code 2.
2026-11-14T13:23:13.7715642Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T13:23:18.1517338Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T13:23:18.1519943Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43599180634

Job 132460246215: verify-readiness

```
2026-11-14T13:21:38.0142544Z PRODUCTION READINESS: {"blocked": ["schedule", "ai_forecasts"], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 6, "required": 10, "status": "BLOCKED"}
2026-11-14T13:21:38.0191542Z ##[error]Process completed with exit code 2.
2026-11-14T13:21:39.2093282Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T13:21:43.1726017Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T13:21:43.1727844Z ##[error]Process completed with exit code 1.
```

## NBA production readiness and stability gate

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43599099510

Job 132459816417: verify-readiness

```
2026-11-14T13:20:00.1693394Z PRODUCTION READINESS: {"blocked": ["schedule", "ai_forecasts"], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 6, "required": 10, "status": "BLOCKED"}
2026-11-14T13:20:00.1753970Z ##[error]Process completed with exit code 2.
2026-11-14T13:20:01.8036554Z PRODUCTION READINESS: {"blocked": ["schedule", "ai_forecasts"], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 6, "required": 10, "status": "BLOCKED"}
2026-11-14T13:20:10.9966044Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T13:20:10.9967991Z ##[error]Process completed with exit code 1.
```

## Full repository static and workflow architecture audit

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43599098203

Job 132459812770: Verify actual production health and invoke bounded free recovery

```
2026-11-14T13:18:41.4462804Z ##[error]Process completed with exit code 1.
2026-11-14T13:26:45.2815437Z ##[error]Process completed with exit code 1.
```

Job 132461904236: Publish evidence and surface audit failures

```
2026-11-14T13:26:54.1137870Z ##[error]Process completed with exit code 1.
```

## Cross-domain Sports-Bot reliability audit (no provider credits)

https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43597984914

Job 132456473029: audit

```
2026-11-14T13:05:28.5922178Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T13:05:28.5923267Z       "code": "MATCHED",
2026-11-14T13:05:28.5924269Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T13:05:28.5925635Z       "code": "RECEIPTS_RETAINED",
2026-11-14T13:05:28.5926904Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T13:05:28.5928080Z       "code": "COMPLETE_SOURCE",
2026-11-14T13:05:28.5929162Z       "code": "STALE_HEALTH_REPORT",
2026-11-14T13:05:28.5930212Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T13:05:28.5973445Z ##[error]Process completed with exit code 1.
```

# Failed jobs inspected

## Run 43626104696, job 132542135002: verify
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43626104696
```text
2026-11-14T18:21:10.5202048Z   "status": "DEGRADED",
2026-11-14T18:21:10.5256779Z ##[error]Process completed with exit code 1.
```

## Run 43626089599, job 132542089600: heartbeat
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43626089599
```text
2026-11-14T18:21:02.7253684Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T18:21:05.9186207Z ##[error]Process completed with exit code 1.
```

## Run 43626064551, job 132542019589: audit
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43626064551
```text
2026-11-14T18:20:48.0656785Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T18:20:48.2605482Z ##[error]Process completed with exit code 1.
2026-11-14T18:20:50.1845240Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T18:20:51.6379031Z ##[error]Process completed with exit code 1.
2026-11-14T18:20:51.6535163Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T18:20:51.6537433Z ##[error]Process completed with exit code 1.
```

## Run 43624930283, job 132538547558: audit
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43624930283
```text
2026-11-14T18:08:51.1493923Z       "detail": "932 historical alternative-tier grades and 4 pending alternative-tier rows excluded from official standard results"
2026-11-14T18:08:51.1495482Z       "code": "NEXT_14_DAYS_ACCOUNTED",
2026-11-14T18:08:51.1495936Z       "detail": "1200 fixed released fixtures saved and next two days reconciled"
2026-11-14T18:08:51.1497774Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T18:08:51.1498217Z       "detail": "status=DEGRADED; check published readiness blockers"
2026-11-14T18:08:51.1499719Z       "code": "MATCHED",
2026-11-14T18:08:51.1500019Z       "detail": "5 verified matched games"
2026-11-14T18:08:51.1501495Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T18:08:51.1502283Z       "detail": "22 exact standard prices lack primary frozen models; 17 have independently preserved research receipts, 5 have no AI receipt"
2026-11-14T18:08:51.1504143Z       "code": "RECEIPTS_RETAINED",
2026-11-14T18:08:51.1504625Z       "detail": "2183 separate historical research receipts (not official grades)"
2026-11-14T18:08:51.1506432Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T18:08:51.1506818Z       "detail": "ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR"
2026-11-14T18:08:51.1508235Z       "code": "COMPLETE_SOURCE",
2026-11-14T18:08:51.1508572Z       "detail": "Provider board reports complete coverage"
2026-11-14T18:08:51.1510254Z       "code": "STALE_HEALTH_REPORT",
2026-11-14T18:08:51.1510615Z       "detail": "captured_at aged 215 minutes; maximum 120"
2026-11-14T18:08:51.1512134Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T18:08:51.1512524Z       "detail": "0 active matchups at last published snapshot"
2026-11-14T18:08:51.1559595Z ##[error]Process completed with exit code 1.
```

## Run 43624840764, job 132538262093: verify
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43624840764
```text
2026-11-14T18:07:53.9608238Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T18:07:54.0584788Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T18:07:54.0899185Z DAMES_PICKS_RELEASE_GATE {"checked_at": "2026-11-14T18:07:54.088975+00:00", "status": "DEGRADED", "checks_passing": false, "release_certified": false, "healthy_streak_started_at": null, "healthy_streak_hours": 0.0, "required_consecutive_hours": 72, "blocking_checks": ["unified_artifacts", "nba_production", "nba_capture"], "checks": {"unified_artifacts": {"state": "DEGRADED", "issues": ["UNIFIED_APP_ARTIFACTS_NOT_READY", "NBA_OR_NFL_ARTIFACTS_NOT_READY"]}, "public_unified_browser": {"state": "READY", "issues": []}, "nba_production": {"state": "DEGRADED", "issues": ["NBA_PRODUCTION_NOT_READY", "NBA_FAILED_PRIZEPICKS_LINES", "NBA_FAILED_CURRENT_PRIMARY_MODEL_COVERAGE"]}, "nba_capture": {"state": "DEGRADED", "issues": ["PRIMARY_STANDARD_COVERAGE_INCOMPLETE"]}, "nba_grading": {"state": "READY", "issues": []}, "published_pick_settlement": {"state": "READY", "issues": []}, "nfl_grading": {"state": "READY", "issues": []}}, "scope": "UNIFIED_DAMES_PICKS_NBA_NFL_RELEASE_GATE", "note": "72h sustained clean artifacts and observed public browser, pretip captures, frozen standard-only grading and current source gates; this does not prove predictive accuracy or zero downtime."}
2026-11-14T18:07:55.4381290Z ##[error]Process completed with exit code 2.
```

## Run 43624489980, job 132537189598: heartbeat
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43624489980
```text
2026-11-14T18:04:11.9990466Z FAIL [('schedule', 'OK'), ('lines_publish', 'OK'), ('lines_fresh', 'OK'), ('lines_coverage', 'OK'), ('picks_frozen', 'OK'), ('capture_integrity', 'FAIL'), ('next_slate', 'WARN'), ('live_scores', 'OK'), ('live_players', 'OK'), ('prizepicks_grade_backlog', 'OK'), ('ai_grade_backlog', 'OK'), ('settlement', 'OK')]
2026-11-14T18:04:16.6782179Z ##[error]Process completed with exit code 1.
```

## Run 43624489940, job 132537189468: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43624489940
```text
2026-11-14T18:04:31.8815024Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T18:04:31.8885347Z ##[error]Process completed with exit code 2.
2026-11-14T18:04:33.6909173Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T18:04:38.3422622Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T18:04:38.3425351Z ##[error]Process completed with exit code 1.
```

## Run 43624295581, job 132536590932: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43624295581
```text
2026-11-14T18:02:29.1440464Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T18:02:29.1494865Z ##[error]Process completed with exit code 2.
2026-11-14T18:02:30.4986895Z PRODUCTION READINESS: {"blocked": [], "degraded": ["prizepicks_lines", "current_primary_model_coverage"], "passing": 8, "required": 10, "status": "DEGRADED"}
2026-11-14T18:02:36.1491185Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T18:02:36.1493044Z ##[error]Process completed with exit code 1.
```

## Run 43623983670, job 132535767102: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623983670
```text
2026-11-14T17:59:29.1494873Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:59:29.1538838Z ##[error]Process completed with exit code 2.
2026-11-14T17:59:30.2922009Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:59:31.9461278Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:59:35.3517557Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T17:59:35.3519199Z ##[error]Process completed with exit code 1.
```

## Run 43623983648, job 132535660940: verify
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623983648
```text
2026-11-14T17:58:47.0255284Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T17:58:47.0313235Z ##[error]Process completed with exit code 2.
2026-11-14T17:58:48.2431801Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T17:58:50.9715461Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T17:58:53.0126460Z ##[error]Process completed with exit code 2.
2026-11-14T17:58:53.0227164Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T17:58:53.0228873Z ##[error]Process completed with exit code 1.
```

## Run 43623953355, job 132535635744: source-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623953355
```text
2026-11-14T17:58:34.1445567Z ##[error]Process completed with exit code 1.
2026-11-14T17:58:40.1304475Z ##[error]NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json
2026-11-14T17:58:40.1307289Z ##[error]Process completed with exit code 1.
```

## Run 43623953313, job 132535566262: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623953313
```text
2026-11-14T17:58:45.8841614Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:58:45.8893021Z ##[error]Process completed with exit code 2.
2026-11-14T17:58:47.5315983Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:58:51.7704628Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T17:58:51.7706374Z ##[error]Process completed with exit code 1.
```

## Run 43623953298, job 132535566387: audit
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623953298
```text
2026-11-14T17:58:21.4484769Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:58:21.6741551Z ##[error]Process completed with exit code 1.
2026-11-14T17:58:23.3335675Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:58:25.0499694Z ##[error]Process completed with exit code 1.
2026-11-14T17:58:25.0672999Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T17:58:25.0674872Z ##[error]Process completed with exit code 1.
```

## Run 43623838143, job 132535210382: audit
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623838143
```text
2026-11-14T17:57:01.4040150Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:57:01.5730629Z ##[error]Process completed with exit code 1.
2026-11-14T17:57:02.9730378Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:57:04.3629389Z ##[error]Process completed with exit code 1.
2026-11-14T17:57:04.3765642Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T17:57:04.3767852Z ##[error]Process completed with exit code 1.
```

## Run 43623748435, job 132535069454: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623748435
```text
2026-11-14T17:56:55.0170540Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:56:55.0231737Z ##[error]Process completed with exit code 2.
2026-11-14T17:56:56.4719050Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:56:58.9446590Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T17:56:58.9448212Z ##[error]Process completed with exit code 1.
```

## Run 43623726238, job 132534853565: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623726238
```text
2026-11-14T17:56:13.2764593Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:56:13.2824488Z ##[error]Process completed with exit code 2.
2026-11-14T17:56:13.9344529Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:56:17.3445195Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T17:56:17.3448141Z ##[error]Process completed with exit code 1.
```

## Run 43623254532, job 132533391195: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623254532
```text
2026-11-14T17:50:50.1729590Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:50:50.1793478Z ##[error]Process completed with exit code 2.
2026-11-14T17:50:51.4952637Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:50:54.3755925Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T17:50:54.3757916Z ##[error]Process completed with exit code 1.
```

## Run 43623254510, job 132533391170: verify
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623254510
```text
2026-11-14T17:50:25.7242980Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T17:50:25.7314702Z ##[error]Process completed with exit code 2.
2026-11-14T17:50:27.2915954Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T17:50:28.5714790Z ##[error]Process completed with exit code 2.
2026-11-14T17:50:28.5894962Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T17:50:28.5896682Z ##[error]Process completed with exit code 1.
```

## Run 43623227915, job 132533312513: audit
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43623227915
```text
2026-11-14T17:50:08.0269934Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:50:08.2065949Z ##[error]Process completed with exit code 1.
2026-11-14T17:50:09.6164274Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:50:11.1323618Z ##[error]Process completed with exit code 1.
2026-11-14T17:50:11.1458433Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T17:50:11.1460875Z ##[error]Process completed with exit code 1.
```

## Run 43622900912, job 132532295723: audit
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43622900912
```text
2026-11-14T17:46:25.5135941Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:46:25.6610738Z ##[error]Process completed with exit code 1.
2026-11-14T17:46:26.4755821Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:46:27.9324738Z ##[error]Process completed with exit code 1.
2026-11-14T17:46:27.9466723Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T17:46:27.9468169Z ##[error]Process completed with exit code 1.
```

## Run 43622808034, job 132532009930: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43622808034
```text
2026-11-14T17:45:59.3739074Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:45:59.3796219Z ##[error]Process completed with exit code 2.
2026-11-14T17:46:00.8226561Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:46:07.0728327Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T17:46:07.0730066Z ##[error]Process completed with exit code 1.
```

## Run 43622801076, job 132531990023: verify
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43622801076
```text
2026-11-14T17:45:21.4298396Z   "status": "DEGRADED",
2026-11-14T17:45:21.4350820Z ##[error]Process completed with exit code 1.
```

## Run 43622726403, job 132531765331: verify
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43622726403
```text
2026-11-14T17:44:28.9057255Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T17:44:28.9125200Z ##[error]Process completed with exit code 2.
2026-11-14T17:44:30.1444356Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T17:44:31.7924676Z {"status": "DEGRADED", "app": {"state": "READY", "issues": []}, "sports": {"NBA": {"state": "DEGRADED", "issues": ["ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL", "CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL"]}, "NFL": {"state": "READY", "issues": []}}}
2026-11-14T17:44:33.0052521Z ##[error]Process completed with exit code 2.
2026-11-14T17:44:33.0199649Z ##[error]Unified Dame's Picks integrity DEGRADED; inspect docs/dames-picks/unified_readiness.json
2026-11-14T17:44:33.0200911Z ##[error]Process completed with exit code 1.
```

## Run 43622700768, job 132531740685: source-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43622700768
```text
2026-11-14T17:44:25.0317859Z ##[error]Process completed with exit code 1.
2026-11-14T17:44:28.0173048Z ##[error]NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json
2026-11-14T17:44:28.0174688Z ##[error]Process completed with exit code 1.
```

## Run 43622689344, job 132531651014: feed-health
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43622689344
```text
2026-11-14T17:44:04.7495722Z       "detail": "932 historical alternative-tier grades and 4 pending alternative-tier rows excluded from official standard results"
2026-11-14T17:44:04.7496712Z       "code": "NEXT_14_DAYS_ACCOUNTED",
2026-11-14T17:44:04.7496923Z       "detail": "1200 fixed released fixtures saved and next two days reconciled"
2026-11-14T17:44:04.7497660Z       "code": "PRODUCTION_NOT_READY",
2026-11-14T17:44:04.7497861Z       "detail": "status=DEGRADED; check published readiness blockers"
2026-11-14T17:44:04.7498546Z       "code": "MATCHED",
2026-11-14T17:44:04.7498687Z       "detail": "5 verified matched games"
2026-11-14T17:44:04.7499345Z       "code": "PRIMARY_FROZEN_MODEL_INCOMPLETE",
2026-11-14T17:44:04.7499875Z       "detail": "22 exact standard prices lack primary frozen models; 17 have independently preserved research receipts, 5 have no AI receipt"
2026-11-14T17:44:04.7500680Z       "code": "RECEIPTS_RETAINED",
2026-11-14T17:44:04.7500895Z       "detail": "2183 separate historical research receipts (not official grades)"
2026-11-14T17:44:04.7501576Z       "code": "GRADE_AUDIT_STATUS",
2026-11-14T17:44:04.7501743Z       "detail": "ALL_ARCHIVED_FORECASTS_ACCOUNTED_FOR"
2026-11-14T17:44:04.7502395Z       "code": "COMPLETE_SOURCE",
2026-11-14T17:44:04.7502573Z       "detail": "Provider board reports complete coverage"
2026-11-14T17:44:04.7503409Z       "code": "STALE_HEALTH_REPORT",
2026-11-14T17:44:04.7503645Z       "detail": "captured_at aged 190 minutes; maximum 120"
2026-11-14T17:44:04.7504303Z       "code": "NO_MISSING_ACTIVE_GAMES",
2026-11-14T17:44:04.7504486Z       "detail": "0 active matchups at last published snapshot"
2026-11-14T17:44:04.7595236Z ##[error]Process completed with exit code 1.
```

## Run 43621379978, job 132527630282: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43621379978
```text
2026-11-14T17:30:07.3665357Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:30:07.3731560Z ##[error]Process completed with exit code 2.
2026-11-14T17:30:08.7762235Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:30:13.0141395Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T17:30:13.0143321Z ##[error]Process completed with exit code 1.
```

## Run 43620835942, job 132525978487: source-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43620835942
```text
2026-11-14T17:23:45.3762241Z ##[error]Process completed with exit code 1.
2026-11-14T17:23:47.5499447Z ##[error]NEXT NBA SLATE NOT READY. Verify archived provider quotes, frozen projections and source completeness in docs/pregame_lifecycle_readiness.json
2026-11-14T17:23:47.5501710Z ##[error]Process completed with exit code 1.
```

## Run 43620784625, job 132525764030: audit
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43620784625
```text
2026-11-14T17:22:57.4981313Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:22:57.7075419Z ##[error]Process completed with exit code 1.
2026-11-14T17:22:58.5138418Z PRIMARY STANDARD LINE RECOVERY: 22 {'NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET': 22}
2026-11-14T17:23:00.7179225Z ##[error]Process completed with exit code 1.
2026-11-14T17:23:00.7323574Z ##[error]CAPTURE INCOMPLETE: some games are missing saved lines, saved AI, or frozen line-backed models. Review docs/tonight_capture_gradeability.json
2026-11-14T17:23:00.7325653Z ##[error]Process completed with exit code 1.
```

## Run 43620738310, job 132525616920: verify-readiness
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43620738310
```text
2026-11-14T17:22:51.6587021Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:22:51.6649327Z ##[error]Process completed with exit code 2.
2026-11-14T17:22:53.2907128Z PRODUCTION READINESS: {"blocked": [], "degraded": ["current_primary_model_coverage"], "passing": 9, "required": 10, "status": "DEGRADED"}
2026-11-14T17:22:57.1463090Z ##[error]NBA live data/projections/line coverage not fully ready. See docs/production_readiness.json
2026-11-14T17:22:57.1465281Z ##[error]Process completed with exit code 1.
```

## Run 43620713940, job 132525543539: audit
https://github.com/damiensandoval77-lang/Sports-Bot/actions/runs/43620713940
```text
2026-11-14T17:22:10.5016681Z ##[error]Process completed with exit code 1.
```

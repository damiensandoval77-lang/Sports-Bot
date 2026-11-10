# Dame's Picks — Single-app production readiness roadmap

**Canonical application:** https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/

The root NBA and /nfl/ standalone HTML pages are redirects only. The separate
NBA and NFL backend collectors, preserved market observations, immutable model
forecasts, final player results and grading ledgers remain necessary inputs.
Do not remove them just because their former frontends were retired.

## Release gates (in implementation order)

| Gate | Exit criterion | Evidence |
| --- | --- | --- |
| 1. Trustworthy pretip capture | Every advertised standard-tier pick has an authentic provider line and an independently generated pretip frozen projection at that **exact** threshold. Quote moves are versioned, not retroactively overwritten. Unsupported markets are explicitly line-only, not recommendations. | `tonight_capture_gradeability.json`, `primary_model_missing_diagnostics.json`, immutable line/model archives |
| 2. Self-healing pipeline | Recoverable stale feed, source-to-site publish, model generation, injury inputs, scoreboard and grading jobs recover automatically with cooldowns, vendor 429 respect, and no duplicate spending. Each repair is followed by independent verification. | GitHub Actions workflow results and incident records |
| 3. True unified-app end-to-end health | Playwright opens the **merged** URL at iPhone width, renders NBA and NFL tabs, tests real standard lines, archived pregame predictions, started-game frozen values, live actuals, grading and Dame's Take. No silent partial exports, empty or stale cards. | `dames-picks/browser_readiness.json`, grading archives and other source-specific probes |
| 4. Release candidate / soak | All required end-to-end checks pass at least **72 consecutive hours** without a failed scheduled poll or manual repairs. Failure resets the timer; missing checks never count as success. | `dames-picks/app_release_gate.json` |
| 5. Native/PWA distribution | Only after Gate 4: installability, performance, auth/privacy boundaries as needed, release version, rollback, offline fallback and App Store/native packaging decisions. | Device QA, release checklist and signed release |

## Current blockers (November 10, 2026)

- NBA frozen capture: 154 unmatched standard thresholds, of which 96 are
  quote moves and 58 have no primary frozen model at all. Never relabel the
  research-only receipts as validated primary model picks.
- Automated browser health is now directed at the canonical merged app; this
  is not itself proof of source freshness or final grade completeness.
- Historical November 9 AI forecast grading **is** reconciled: 620 graded,
  136 independently verified exclusions, 0 pending. Keep it accurate on
  future nights rather than relying on old JSON.
- NFL frozen grading must use standard-only lines, never goblin/demon thresholds.

## Release policy

`READY` in an individual source is not the same as release-ready.
The combined release verdict must require current evidence for both leagues,
fresh NBA readiness, exact-line capture, grading, public browser rendering,
and a sustained uninterrupted healthy streak. Never substitute synthetic data
or optimistic status for missing verified source observations.

**Cost policy:** PrizePicks top-up access is authorized even when the monthly
credits header says zero. Actual provider response determines access. Preserve
the existing bounded fetches and 429 stop behavior. Run free reconciliation
before any additional paid refresh.

**Recovery policy:** Detect → classify → route to the real producer → wait for
completion → verify published output → retain incident until healthy. Merely
rerunning the same audit is not recovery.

**User experience:** One canonical Dame's Picks link. Both sports in one
application. Stable, truthful loading/error states. Never ask users to
manually run nightly refreshes as part of normal operation.

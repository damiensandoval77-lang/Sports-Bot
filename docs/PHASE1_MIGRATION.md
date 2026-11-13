# Phase 1 reliability migration — GitHub-first

## Purpose
Keep the existing NBA prop board available without relying on monthly Replit Agent credits. GitHub repository is the canonical source, but **do not assume the newer Replit app is synced**: compare the Replit app against GitHub before any cutover.

## Verified initial audit (2026-11-09)
- GitHub dashboard exists at `docs/index.html`.
- `docs/data.json` reported 12 available NBA events, 0 checked, and 11 remaining provider credits, with a 2026-11-07 timestamp. This is inadequate for full-slate claims.
- `docs/live_player_tracking.json` reported no active matchups as of its Nov 9 capture. No games active may be normal; don't mislabel that as failure.
- `docs/projection_upgrade_status.json` explicitly reported research-only, no fresh pregame board.
- Data files are public. **Never store API keys or private customer data in docs.**

## Phase 1 milestones
1. **Detect problems, don't silently claim success.** Audit feed age, slate game coverage and live matchup freshness; run checks on pull requests and periodically.
2. **Protect progress.** Inventory recent Replit-only changes before any environment shutdown. Save upstream code and secrets *names* (never values) securely.
3. **Reliable pregame board.** Cover full NBA schedule, preserve real sportsbook/PrizePicks line source provenance, time-lock projections, and show explicit missing-data diagnostics.
4. **Reliable live tracker.** Store pregame selections and separately capture live player stats to compare against saved picks. GitHub Actions schedules are not strict real-time; evaluate short-poll serverless or other free-tier alternative, rate limits, and API credit budgets before claiming live performance.
5. **Automatic grading.** Final box scores grade only saved predictions, with idempotent backfills and corrections; monitor ungraded outcomes.
6. **Verified cutover.** Only switch dashboard source after checks pass on multiple actual slates, no duplicate/blank boards, documented secrets migration and rollback plan.

## Cost guardrails
- GitHub Pages is static hosting, not a permanently running server.
- GitHub Actions scheduled workflows can be delayed; avoid pretending they provide second-by-second live tracking.
- PrizePicks and sportsbook API charges/limits are separate from compute costs.
- API keys belong in encrypted repository or deployment secrets, not client-side JavaScript or committed files.
- Keep the previous deployment accessible until the replacement demonstrates equivalent output.

## Health audit
`python iphone_bot/health_audit.py` prints a JSON diagnosis and exits nonzero on a critical data-coverage error. `python -m unittest discover -s iphone_bot/tests -p 'test_health_audit.py' -v` runs isolated tests. `phase1_feed_health.yml` schedules checks and opens visibility in GitHub Actions; scheduled jobs on default branch activate after this work is merged, not on an unmerged feature branch. Alerts depend on GitHub notification preferences.

**Current status:** Diagnostic guardrails only; this does not repair the existing upstream feeds, deploy the Replit app, or guarantee zero-cost near-real-time operation.

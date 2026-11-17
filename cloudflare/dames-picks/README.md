# Dame's Picks on Cloudflare — safe migration, phase 1

**Status (November 17, 2026):** The separate `dames-picks-staging` Worker is deployed and its public website verified. The owner created D1 database `dames-picks-staging-db` and connected it through the Cloudflare dashboard as `DB`. The database ID is versioned in `wrangler.jsonc` and the scheduled Worker will perform a one-time, idempotent staging-schema bootstrap. Actual table creation and Cron writes must be verified on the live Worker after this configuration deploys. The existing GitHub Pages sports website and Federal Briefing remain unchanged.

## Keep both sites in one Cloudflare account — without coupling them

| Project | Repository | Cloudflare Worker | Data/automation |
| --- | --- | --- | --- |
| Federal Briefing | `damiensandoval77-lang/federal-briefing-mvp` | `federal-briefing-mvp` (existing) | Congress.gov Worker/API + twice-daily GitHub catalog sync; don't alter it |
| Dame's Picks | `damiensandoval77-lang/Sports-Bot` | `dames-picks-staging` (new, staged only) | New independent Cron heartbeat; sports collectors and D1 binding still pending |

Use the **same Cloudflare account** to create the second Worker, but **different app names, databases, credentials, cron schedules and release gates**. Billing and account-wide Worker limits are shared; usage must be monitored by application. Creating a Worker on the wrong Cloudflare account won't make it share billing with Federal Briefing.

## What's already checked in

- `wrangler.jsonc`: one staged Worker; explicit `*/15 * * * *` Cloudflare cron, no paid calls, and original website static assets.
- `src/worker.js`: `/healthz`, `/api/v1/health` and `/api/v1/status`. Missing D1 returns 503 readiness instead of a fake healthy result. Cron writes an audit heartbeat only if DB binding/migration exists.
- `scripts/build-assets.mjs`: copies the **existing one unified** NBA/NFL/Tennis website and public snapshots to a staging asset bundle; never touches old production. Staging UI displays a warning and is noindexed. Large or missing required source files fail the build rather than silently publish incomplete forecasts.
- `migrations/0001_bootstrap.sql`: seven source-health rows initially `not_connected`; persistent scheduler runs.
- `tests/worker.test.mjs`, GitHub staging CI: prove isolation, no paid requests, real D1 schema and snapshot-build completeness.

**Nothing here makes game statistics, PrizePicks lines, or models automatically refresh yet.** Phase 1 only demonstrates deployable website assets, health checks and an independent scheduled heartbeat. The backend must still be connected to permitted sports/odds sources and inference compute.

## Cloudflare dashboard connection — owner's action

1. Open [Cloudflare Workers & Pages](https://dash.cloudflare.com/?to=/:account/workers-and-pages) using the **same account** that contains `federal-briefing-mvp`.
2. Select **Create application → GitHub**, and choose `damiensandoval77-lang/Sports-Bot`.
3. Worker name: **`dames-picks-staging`** (it must match the `name` in `wrangler.jsonc`).
4. **Root directory:** `cloudflare/dames-picks`; **production branch:** `main`.
5. **Build command:** `npm run build`; **deploy command:** `npx wrangler deploy`.
6. Leave runtime secrets blank for this phase. **Do not turn on paid APIs, billing, or a public custom domain.** The Worker will get its own `workers.dev` preview URL. It is not the final domain yet.
7. Check `/healthz` returns `stage: staging` and `provider_collection_active: false`. Check `/api/v1/status` returns HTTP 503 `setup_required` until D1 is provisioned. Confirm `/dames-picks/` visually matches the approved Concept #3 and Board/Live/Tracker/Saved/Tennis still navigate.

Cloudflare's Build configuration uses **Root directory**, **Build command** and **Deploy command**. GitHub remains the repository, but Cloudflare becomes the public application host after verified cutover.

## D1 / independent automation — bound database and one-time initialization

- Database name: `dames-picks-staging-db`; binding: `DB`; Cloudflare D1 database ID: `7ccf157d-aab6-4efd-afb8-d9dfb69d8af8`. The ID is a public configuration identifier, **not a secret**.
- This database is wholly separate from Federal Briefing and is tracked in `wrangler.jsonc` so future automated Worker deployments retain the binding.
- The first successful Cloudflare scheduled Cron with D1 attached will initialize *only the first bootstrap schema* using the checked-in versioned `0001_bootstrap.sql`, if the tables or seven source rows are missing. It then writes the first `staging-heartbeat` event. Subsequent Crons skip the bootstrap and write only new heartbeats every 15 minutes.
- This bootstrap runs only from Cloudflare's **internal scheduled handler**; there is no public migration or write endpoint. On failure, `/api/v1/status` reports `database_unavailable` and Cron records no false success.
- Verify the live `/healthz` endpoint changes to `database_binding_present: true` after the GitHub-triggered deployment.
- After the scheduled trigger runs, `/api/v1/status` must respond HTTP 200 with `database: connected`, exactly seven source records (initially `not_connected`), and a real `scheduled_heartbeat`. Do **not** mistake `collectors_not_ready` for failure: no game or paid-data collectors have been activated yet.
- A Cloudflare Cron trigger may take time to propagate; no claim of autonomous operation is made until a real scheduled heartbeat is observed and its timestamp is within the expected interval.
- If the internal first-Cron bootstrap fails, use the versioned remote migration in the Cloudflare account, from this directory: `npx wrangler d1 migrations apply dames-picks-staging-db --remote`. Applying the idempotent initial migration after Cron bootstrapping is safe and records it in `d1_migrations`.
- Later schema changes **must** use regular reviewed versioned migrations; the Worker auto-bootstrap intentionally handles *only* `0001_bootstrap.sql`.
- Keep `PAID_PROVIDER_REQUESTS=disabled`. Do not add secrets or enable API polling during schema verification.

## Migration phases and launch gates

1. **Staging Worker and site:** Git-connected, public test at Workers URL, real phone+desktop screenshot comparison to Concept #3, existing sports dashboard still live on GitHub Pages.
2. **D1 + Cron:** Heartbeats independently written by Cloudflare, watchdog flags stale/missing feeds; test Cron retry and permission failures.
3. **Data collectors:** Contract-test standard PrizePicks/Underdog market coverage (The Odds API test), verified ESPN/boxscores, injuries, canonical ID mapping; cache provider responses and impose account/credit limits. Importing a stale GitHub JSON snapshot must never count as a fresh observation.
4. **Model / frozen forecasts:** Keep Python training/inference on compatible compute. Cloudflare schedules/coordinates jobs and persists immutable pregame projections, market snapshots and eventual confirmed grades.
5. **Reliability gate:** Seven reconciled NBA game nights + two NFL slates with complete capture, DNP handling, postgame grades and outage recovery; monitor full source lag, model gaps, spending and live phone view.
6. **Public cutover:** Move a cleared domain to the **single** Cloudflare Dame's Picks Worker and redirect GitHub Pages only after live evidence; keep a rollback path. Leave Federal Briefing unaffected.

## Cost and operational safeguards

- No subscription, extra Cloudflare paid tier, Odds API spend or player headshot license authorized by this patch.
- Default `PAID_PROVIDER_REQUESTS=disabled` is enforced by the staging Worker.
- Separate Cloudflare Workers operate independently, but **Cloudflare account-level usage limits and billing are shared**.
- No copied player portraits are needed; when images are unavailable, use source-licensed team logos or an abbreviation badge.
- Existing Federal Briefing catalog still uses GitHub-scheduled publishing; it is **not** automatically migrated by this sports change.
- New site launch requires independent staging deployment and user-visible phone confirmation. A GitHub PR/CI success is not a deployed Worker.

## Useful docs

- Cloudflare Workers Git builds: https://developers.cloudflare.com/workers/ci-cd/builds/configuration/
- Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- D1 migrations: https://developers.cloudflare.com/d1/reference/migrations/
- Cron handler: https://developers.cloudflare.com/workers/runtime-apis/handlers/scheduled/

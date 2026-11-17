# Dame's Picks on Cloudflare — safe migration, phase 1

**Status:** Repository staging infrastructure only. No Cloudflare account credentials or billing changes used; **no Worker is deployed yet**. The existing GitHub Pages sports website and the existing Federal Briefing Cloudflare Worker remain unchanged.

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

## D1 / independent automation — next owner setup

The D1 database **does not exist yet**. Once the staged Worker is live:
- Create one new database (suggested name `dames-picks-staging-db`) in **D1**, not in Federal Briefing.
- Bind it to the Worker as `DB`; record the returned nonsecret database ID in `wrangler.jsonc` under `d1_databases` (we must not invent a UUID).
- Apply the checked-in D1 migration using Wrangler, e.g. from `cloudflare/dames-picks` after the binding exists:
  `npx wrangler d1 migrations apply dames-picks-staging-db --remote`
- Check `/api/v1/status` reads seven `not_connected` source rows and reports the latest `staging-heartbeat` scheduled run within a few Cron intervals.
- Do **not** mark the model, odds, grading, or game feeds healthy based on a scheduler heartbeat alone. The success criteria are independent data observations and completed frozen/graded game nights.

Any API tokens should be Cloudflare **runtime secrets**, never GitHub commits or browser code. No key is needed in this phase.

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

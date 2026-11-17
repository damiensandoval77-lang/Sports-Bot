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
- The staged Worker supports idempotent, internal-only bootstrapping of reviewed `0001` and `0002` migrations. Subsequent schema changes must use versioned D1 migrations with explicit review.
- Keep `PAID_PROVIDER_REQUESTS=disabled`. Do not add secrets or enable API polling during schema verification.

## The Odds API market expansion (staging / read-only until owner opt-in)

**What this adds:** a catalog of documented standard NBA/NFL player-prop markets, read-only Market Explorer at `/dames-picks/market-explorer.html`, budget/market API endpoints, and a future optional Cloudflare scheduled provider collector. The Odds API provides market quotes and team scores, NOT verified individual player box scores, minutes, usage, injuries, teammate on/off, defense ratings or AI projections.

- **NBA core markets:** player points, rebounds, assists, PRA. Additional documented keys displayed in the catalog include threes, steals, blocks, turnovers, combined PR/PA/RA, free throws and more.
- **NFL core markets:** receptions, receiving yards, rushing yards, passing yards, passing touchdowns. Catalog also lists pass attempts, completions, interceptions, combined yards, longest reception and other supported markets.
- **Standard-line only:** `_alternate` markets are not requested or stored; no goblin/demon or non-default-multiplier selections. A line must have exactly one matching Over and Under entry for the same player, event, market and threshold. Market timestamps must precede tipoff. The provider may not actually list every documented market for every event.
- **No fake model forecasts:** source player identities start unverified because a market quote does not include a trustworthy canonical player/team ID. Odds cannot grade an AI pick or replace a frozen pregame forecast without a separately verified exact player+team+event mapping. Bookmaker prices are not the model's hit estimates; DFS prices are indicative and suppressed from implied-probability charts.
- **Immutable saved observations:** `migrations/0002_odds_markets.sql` creates append-only quote history, a monthly/daily credit ledger and request receipts. Worker-internal Cron tries idempotent first-time 0002 schema setup; public requests never mutate tables.
- **Read-only endpoints:** `GET /api/v1/odds/catalog` (no D1 or provider cost), `GET /api/v1/odds/board?league=NBA|NFL` (latest pregame standard D1 quotes observed within 90 minutes, or an honest empty/unavailable status), `GET /api/v1/odds/budget` (recorded credit usage and caps). Reading the site spends ZERO The Odds API credits.
- **Explicit spend gate:** `PAID_PROVIDER_REQUESTS=enabled`, `ODDS_API_COLLECTION=enabled`, a stored Cloudflare **secret** `ODDS_API_KEY`, and owner-approved positive `ODDS_API_MONTHLY_CREDIT_CAP` / `ODDS_API_DAILY_CREDIT_CAP` must ALL exist. The current default has paid requests DISABLED. An accidental API key alone does not activate polling. Never put the secret in GitHub, a public URL or an HTML file.
- **Cost control:** Only `prizepicks,underdog,fanduel,draftkings` (four exact bookmaker keys, one billed group). The API's zero-credit event-list endpoint finds upcoming games, followed by at most ONE event-level paid player-prop request per scheduled run. Core NBA requests cover four markets; core NFL requests five. Expanded markets require explicit keys in `ODDS_API_EXTRA_MARKETS_NBA` and `ODDS_API_EXTRA_MARKETS_NFL`, up to two extras each. No automatic historical market requests. Skip games with a recent attempt; exclude tipped-off games. Atomic D1 reservation prevents a call when monthly/daily budgets cannot accommodate its *maximum* cost. Actual provider header `x-requests-last` settles credit usage; absent headers conservatively charge the maximum reserve.
- **Confirm coverage before canceling the old provider:** Compare genuine standard PrizePicks/Underdog market lines for at least several full NBA game nights and NFL slates, including missing games, provider quote freshness and cost. The current collector is not replaced merely because the new API lists support.
- **External sources:** [bookmakers / DFS alternates](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html), [market keys](https://the-odds-api.com/sports-odds-data/betting-markets.html), [v4 credits and events](https://the-odds-api.com/liveapi/guides/v4/).

### Safe owner activation, *only after staged coverage tests and approval*

1. First verify `/api/v1/status` shows real D1 heartbeat, then `/api/v1/odds/budget` confirms the 0002 schema. If 0002 cannot initialize, apply the checked-in versioned migration through Cloudflare D1 before enabling any provider.
2. Create a **free** The Odds API key and store it as the Cloudflare Worker **secret** `ODDS_API_KEY`. Do not send the secret in ChatGPT or commit it.
3. Start with explicit small caps appropriate for the approved test. For example `ODDS_API_MONTHLY_CREDIT_CAP=100`, `ODDS_API_DAILY_CREDIT_CAP=12`, and leave both paid switches disabled during configuration.
4. After owner approves actual credit use, enable both switches only on this staging Worker. Observe request receipts, `x-requests-last`, D1 line coverage and source freshness. Never enable the production site while tests are incomplete.
5. Keep heavy Python model training and inference in appropriate compute, not Cloudflare's odds collector. Keep Federal Briefing untouched.

## Existing The Odds API key — verification without credit usage

The owner entered an existing API key into **Cloudflare → `dames-picks-staging` → Settings → Variables and Secrets**, using the encrypted secret name `ODDS_API_KEY`. The secret value must **never** be committed, displayed in browser JSON, pasted into chat, or copied into GitHub Actions.

The next Cloudflare scheduled run checks this key **using `GET https://api.the-odds-api.com/v4/sports/` only**. The Odds API v4 documentation identifies that endpoint as costing **zero usage credits**, with authentication via the `x-api-key` HTTP header. An authentic zero-credit response must contain `x-requests-last: 0`. A successful response reports NBA/NFL sport availability and the quota remaining from response headers; no raw response or key is stored.

- Only Cloudflare's **private 15-minute scheduled handler** makes the request. Opening or refreshing the website makes no Odds API request.
- Verification results are written to the existing D1 `scheduler_runs` table as job `odds-api-free-key-check` (safe status, provider HTTP code, last-call credits, remaining credits and NBA/NFL active flags; never the secret).
- After success, the free probe runs at most **once every six hours**. Failed checks can retry after 30 minutes; adding a new key after a missing-key result allows an immediate next-Cron retry. A status older than eight hours is marked stale and must not count as current authentication.
- `GET /api/v1/odds/connection` reads the saved receipt and reports `key_authentication_verified` without any upstream request. The endpoint is **read-only**.
- **This verifies only credentials and a free list-of-sports endpoint.** It does not confirm access to PrizePicks, Underdog, betting lines, paid prop markets, injuries, actual player performance or AI forecasts. The existing collector remains disabled.
- The staging `wrangler.jsonc` explicitly retains `PAID_PROVIDER_REQUESTS=disabled`; `ODDS_API_COLLECTION` remains unset. Do not authorize or enable paid odds requests until we separately set a small daily/monthly allowance and verify real standard-line coverage.
- To inspect the deployed key check after a Cron: `https://dames-picks-staging.damiensandoval77.workers.dev/api/v1/odds/connection`. `awaiting_free_check` means the deployed Worker hasn't completed its first verification yet; `secret_not_configured` means the Worker cannot see a valid secret under that name; `authentication_rejected` indicates an invalid/refused credential; `authenticated` + `last_call_credits: 0` confirms a live free check.
- The live D1 schemas, periodic heartbeats and other services are independent from this credential validation. Federal Briefing and the GitHub Pages sports production site are not changed.

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

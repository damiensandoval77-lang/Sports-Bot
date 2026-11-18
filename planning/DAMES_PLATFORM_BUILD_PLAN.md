# Dame's Picks — Sports Platform Build Plan

Research and first implementation: November 16, 2026.
Branch: `feat/sports-platform-foundation-20261116`.
Production entry: `docs/dames-picks/index.html`.

## 1. What exists, what changed, and what is not verified

The inspected production HTML contains NBA, NFL and Tennis selectors and uses `feeds.js`, `live_direct.js`, `dames_take.js`, `provisional.js`, `short_history.js` and `tennis.js`. Its release marker when inspected was `dp-tennis-match-list-20261115-r52`. Its refresh function reads multiple independent JSON/CSV artifacts. This is a focused frontend inspection, not a full architecture, security, model or live-data audit.

This first change adds `docs/dames-picks/platform-preview.html`, an isolated, self-contained UI foundation with Overview, Sports Center, Player Intelligence, Dame's AI and Prediction Lab. It preserves the actual NBA/NFL/Tennis scope. It does not modify the production index, models, feeds, grading ledgers, credentials or workflows. The preview makes no network or paid API calls. AI generation and billing are not enabled.

Local Chromium checks cover all five screens at 320, 393, 768 and 1440 pixels, plus sport selection, filters, empty states, safe text rendering, disabled AI generation and invalid-route recovery. These are NOT real iPhone/Safari, CI, deployed-site or live-game verification. Production retrieval through the available web reader failed; do not claim the deployed redesign is verified.

The preview is a temporary feature-branch review artifact, not a second product. After parity and deployment tests, move the approved shell into the existing app entry point and remove or redirect the preview. Keep one merged production app.

## 2. Product and design contract

Use the owner's four-panel reference: near-black background, rounded dark panels, white headings, purple research/AI accents and restrained green/red result states. Use a desktop sidebar and phone bottom navigation. Preserve readable text, keyboard focus, reduced-motion behavior and safe-area spacing. Home is a useful gateway, not an endless list of picks.

| Area | First working integration | Later expansion |
| --- | --- | --- |
| Sports Center | Schedule, game status, scores, player box scores, injury status and timestamps | Team pages, news links, play-by-play, favorites |
| Player Intelligence | Search, sport-specific game logs, L5/L10/L15/season, comparisons and sample sizes | Teammate on/off, minutes ranges, rest/home/away filters, richer opportunity data |
| Dame's AI | Structured read-only queries over verified records, citations and data timestamps | Saved questions and bounded personalized alerts |
| Prediction Lab | Existing standard-line projections, Over/Under, hit estimates, Dame's Take, saved picks and grades | Versioned model comparisons and prospective calibration reporting |

Retain the old board/tracker/saved functions inside Prediction Lab; place live game views in Sports Center and player detail in Player Intelligence. Preserve bookmarks or provide an explicit migration. Retain Tennis functionality without pretending its statistics or settlement rules are the same as NBA/NFL.

Dame's Take remains directly beneath Dame's Projection, short and conversational. Use Over/Under, not More/Less; Under is red. Show on-pace totals separately from model forecasts. Do not turn a historical hit fraction into a matchup probability. Do not remove meaningful missing-data or calibration warnings merely to make the screen look finished.

Empty states must distinguish: loading; provider unavailable; stale; unknown player mapping; no games actually scheduled; no matching filters; and feature not connected. Missing values are null/dashes, never zero. Graph placeholders are explicitly labeled and do not contain invented player performance.

## 3. Verified source directory and decisions

Links were reviewed November 16, 2026. A documented endpoint is not proof that our account has access, its current slate is complete, or its freshness meets our targets. No new provider was purchased or connected in this change.

| Source | Verified information and intended role | Decision / remaining checks |
| --- | --- | --- |
| [StatsHub features](https://www.statshub.com/features) and [Prop Screener](https://www.statshub.com/prop-screener) | Public soccer research interface includes market/direction, L5/L10/L15, date, league, lineup and odds filters. | Use workflow ideas, not copied branding, assets or scraped proprietary data. These are research-interface references, not evidence of our NBA/NFL data coverage. |
| [StatsHub Odds API](https://www.statshub.com/odds-api) | Advertises cross-sport odds/props/scores. Published Solo plan starts at GBP 49/month with two selected bookmakers and 5,000 calls/hour. | Defer on the USD 100 startup budget. Exact PrizePicks/Underdog standard-line coverage, historical retention and redistribution terms remain unverified. Vendor marketing performance numbers are not our measured service levels. |
| [BALLDONTLIE NBA](https://nba.balldontlie.io/) and [NFL](https://nfl.balldontlie.io/) | Documented APIs for NBA/NFL; NBA documentation includes players, games, player stats, tracking, injuries, box scores, lineups and props. Endpoint availability depends on plan. | Shortlist for a small coverage test. Check the current account-tier table and checkout before any purchase; this plan does not assume a free tier includes all endpoints. Keep keys server-side. |
| [BALLDONTLIE terms](https://www.balldontlie.io/terms.html) | October 20, 2026 terms explicitly permit paid apps, analytics and AI uses, while restricting substitute data APIs and credential sharing. Third-party rights and best-effort data limitations remain. | Suitable candidate for this product, not an official league endorsement or guaranteed feed. Do not use it as sole evidence for wager settlement. |
| [nflverse](https://github.com/nflverse) and [update schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) | Most datasets use CC-BY 4.0; FTN data has separate share-alike terms. Player/play-by-play updates are largely postgame/nightly; schedules update more often. Participation data from 2023 onward is supplied after the postseason, not during the season. | Reuse appropriate attributed historical/weekly/schedule datasets. Review EACH dataset's license. Do not promise live player tracking or in-season routes from delayed participation files. Avoid adding FTN-derived features until obligations are understood. |
| Existing repository ESPN/NBA and other source integrations | Their existence is visible in frontend/feed code and prior project work. | Preserve during UI work, but access is not commercial permission. Verify upstream terms, current endpoints, rate limits, coverage and fallback rights before paid release. Not audited here. |
| Existing PrizePicks partner integration | The project already has quote/standard-line and pregame archive paths. | Confirm the actual provider/account, permissions, remaining credits and standard/Goblin/Demon flags. No secret inspection or paid polling in this change. Never auto-enable a paid fallback. |
| [Cloudflare Pages pricing](https://developers.cloudflare.com/pages/functions/pricing/) | Static asset requests are free/unlimited; Functions share Workers usage limits, including the Free daily allowance. | Preferred low-cost hosting candidate, subject to account setup and terms. A Python ML worker is separate; do not assume large Python models can simply run in Pages Functions. |
| [GitHub Pages restrictions](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) | GitHub Pages prohibits use as free hosting for an online business or commercial SaaS. | Keep GitHub for code. Move production hosting before subscription launch. Current Pages is not the planned commercial destination. |
| [Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines) | Hobby is restricted to non-commercial personal use. | Do not budget a paid subscription business on Vercel Hobby. |
| [Supabase pricing](https://supabase.com/pricing), [free-project pausing](https://supabase.com/docs/guides/platform/free-project-pausing), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security) | Free plan has quotas and low-activity pausing; RLS enables database access controls. | Candidate for Postgres/Auth. Capacity, backups, recovery and entitlement tests required. Never expose service-role credentials. |
| [Railway billing](https://docs.railway.com/pricing/understanding-your-bill) | Hobby has a USD 5 minimum usage commitment, not a fixed all-inclusive worker bill. | Profile memory/CPU of existing models before purchase; use a spend cap and explicit owner approval. Training can remain a separate batch task. |
| [Stripe subscription webhooks](https://docs.stripe.com/billing/subscriptions/webhooks) and [restricted businesses](https://stripe.com/legal/restricted-businesses) | Subscription lifecycle needs server-side event processing. Stripe lists gambling/prize-related restrictions. | Accurately describe the actual analytics/props business and confirm eligibility. Do not conceal its purpose through labels. We do not operate wagers, prizes or deposits. Billing remains disabled. |

For any new provider, record: account owner, approved endpoints, permitted commercial display/retention/AI use, attribution, plan, monthly cap, request quota, actual refresh cadence, stable player/game IDs, standard-line markers, and fallback rights. Store the reviewed terms URL and review date with this registry. Do not put keys in this document or a public repo.

## 4. Statistics we need

### NBA

First: player/game/team IDs; start time and game state; minutes; points, rebounds, assists, steals, blocks, turnovers; shooting makes/attempts; standard prop line and direction; game logs; availability and expected minutes; team pace and defensive context; position grouping. Compute combined stats such as PRA from matched components in the SAME game and ruleset.

Next: usage, potential assists, rebound chances, touches, possession-based metrics and teammate on/off. Treat tracking/opportunity fields as a separate coverage/licensing requirement. They are not safely reconstructed from a basic box score. Defense-versus-position is a contextual team measure, not proof of the individual defender guarding a player. Show source, season/window, sample size and calculation definition.

### NFL

First: schedule/game/team/player IDs; player position and availability; passing attempts/completions/yards/TD/INT; rushing attempts/yards/TD; targets, receptions, receiving yards/TD; fumbles; team pace/game context and fantasy scoring rules. Add snaps, target share and red-zone opportunities only when denominator and period coverage are valid.

Next: routes run, route participation, targets per route, yards per route and air-yard/ADOT context. Never substitute snap count for routes. The documented nflverse participation delay means current-season routes need another permitted source or must stay unavailable. Existing HeatRadar use stays manual-only; no scraping or automated endpoint access.

### Shared

Every record needs provider, provider ID, canonical ID, sport/league, game ID, event time, observed_at, ingested_at, source update/version, completeness, freshness and provenance. Missing-field and provider-failure reasons must survive normalization. Schedule dates use explicit league/slate time zones and store UTC start times.

## 5. Target architecture and data contracts

Use a modular app and one database first, not an expensive microservice rewrite:

`permitted sources -> scheduled collectors -> validation/normalization -> Postgres -> read API/cache -> website`

`frozen pregame snapshot -> model inference -> immutable forecast -> observed final result -> versioned grade -> performance aggregates`

- `source_registry`: documented rights, endpoint coverage, cadence, quota and review status.
- `teams`, `players`, `provider_id_map`: canonical IDs and effective-dated identity mappings; never fuzzy-join different players into a live result.
- `games`: authoritative schedule, start time, sport-specific status, score and postponement handling. A missing prop line cannot remove a scheduled game.
- `stat_observations`, `injury_observations`: source times, source versions and provenance. New ingestion time alone does not make an old observation newest. Preserve legitimate official downward corrections as versioned observations.
- `market_snapshots`: append-only standard-line quotes, provider/market identity, line tier, timestamp and source.
- `model_versions`, `forecasts`: projection, uncertainty, exact line/direction, input cutoff, model/version, feature hash, calibration status and pregame freeze time.
- `grade_events`: append-only result/void/push/DNP/correction records with evidence and settlement rules. Revisions do not overwrite the original forecast.
- `profiles`, `watchlists`, `subscriptions`, `billing_events`: user ownership and server-managed entitlements. Market/model data is not user-writable.
- `job_runs`, `data_quality_events`: expected workload, counts, durations, gaps, failures and repair state.

Expose a versioned API contract for games, players/game logs, player comparisons, predictions, grades and system freshness. Start with a compatibility adapter around existing files before changing the data store. Read both implementations in shadow mode and compare IDs, counts, sums and sample records. Only retire Git data publishing after parity and rollback tests pass.

Security requirements: private premium storage/API; RLS on exposed tables; no service key in browser; no premium rows embedded in static HTML, public JSON or client bundles. Test anonymous, free, paid, canceled and cross-user access. Protect views and storage policies too. Keep projections requiring secrecy out of public Git history going forward; a UI paywall cannot make previously published data secret.

Reliability requirements: timeouts; bounded exponential backoff with jitter; respect Retry-After; idempotency keys; independent jobs for collection, forecasting and grading; a durable run ledger; provider circuit breakers; atomic publication; dead-letter/reconciliation handling; monitored stale-data alerts. A process supervisor may restart a worker, but an infinite try/except loop is not the recovery design.

Cache shared data server-side so 100 visitors do not cause 100 provider requests. Poll live UI at the desired 30-second interval only when useful, with visibility-aware behavior; display the actual provider age. This is a design target, not a verified source cadence. Distinguish unavailable from stale, and show the last successful timestamp without pretending it is live.

## 6. Ordered implementation and acceptance gates

### P0 — UI foundation (this change)

Review `platform-preview.html`; run local tests. No production replacement or data contract changes. Owner screenshot direction governs styling. Before promotion, separate modules/assets as needed and use an appropriate production CSP rather than treating this offline preview's inline allowances as the final security configuration.

### P1 — Integrate existing data without losing features (next)

1. Inspect every loader, frontend export and related test; map old board/live/tracker/saved/player detail into the new sections. Verify the actual Pages/deployment workflow and cache/release mechanism.
2. Build `platform-data` adapters against current NBA, NFL and Tennis outputs. Preserve known standard-line, timestamp, team-alias and grade eligibility rules. Tests must cover missing artifacts, expired quotes, duplicates, DNPs, injuries, date boundaries, postponed games, corrections and mismatched IDs.
3. Connect Sports Center schedule and verified box scores first, then the current Prediction Lab ledger, then player logs. Do not silently fetch a paid provider to fill gaps.
4. Compare old/new screens and counts on the same input fixtures. Confirm bookmarks, filters and player deep links survive. Capture phone-size and desktop screenshots of all routes.
5. Stage on the intended hosting target. Verify release marker/asset hashes and all routes through the deployed URL, including WebKit/Safari testing; actual phone confirmation is distinct from emulation.

Gate: no regression in existing features; correct real-data identities/timestamps; truthful stale/missing displays; screenshots reviewed. Missing provider permission blocks commercial use even if a test response succeeds.

### P2 — Reliable data service and migration

Owner-controlled hosting/database accounts and secrets; budget cap; schema migrations; backups and tested restore; RLS tests; one permitted source connected at a time. Replay existing frozen ledgers idempotently into Postgres, reconcile totals and keep reversible old reads until parity holds. Stop Git commits for operational data only after the replacement is proven. Keep code, tests, model-version metadata and appropriate batch jobs on GitHub.

Gate: an unattended pregame-to-final cycle with recorded health evidence; outage/retry/restart tests; no lost or double-counted grades. Recover historical grades only from actually recorded pregame predictions. A forecast generated after a result is known cannot enter prospective performance.

### P3 — Useful player research and transparent models

Ship game-log charts, comparisons and contextual filters before more sports. Keep estimated probability separate from descriptive recent hit rate. Evaluate chronological out-of-sample and then prospective results by sport/stat/line/model version; include sample sizes, calibration curves, Brier/log-loss metrics and baselines. Do not claim calibrated accuracy or positive ROI from a small sample or model fit alone. State denominators; exclude void/push/DNP from win-loss denominator and report separately.

Gate: users can answer actual research questions; feature definitions and sample sizes are visible; missing opportunity/tracking data is not fabricated.

### P4 — Data-grounded AI

Implement read-only allowlisted queries, not arbitrary SQL generated by the model. Retrieve validated data and do calculations deterministically; the language model explains the returned facts. Attach source IDs, time window and last update to each answer. Return an insufficient-data response when required records are missing. Add per-user limits, token caps, server-side keys, prompt-injection defenses and a spend kill switch. Cache repeat public questions where rights permit. Respect premium entitlements in retrieval as well as display.

Gate: adversarial and factual tests; no invented stats, unauthorized records or hidden paid API requests. Until then the visible AI composer stays disabled.

### P5 — Commercial readiness and a small paid pilot

Move off GitHub Pages before monetization; complete provider-rights/account review; accurately disclose the business to the payment processor; privacy/terms/cancellation/refund flow; email ownership and deliverability; verified signed webhooks and idempotent event processing. Handle payment failures, renewal, cancellation, refunds and out-of-order events. Client checkout redirects do not grant paid access. Test all states before enabling billing.

Invite a small group first and measure successful research sessions and repeat use, not just signups. Proposed release observation: seven consecutive NBA game nights and two NFL slates with captured/frozen/graded records reconciled, plus no unresolved critical access-control or correctness bugs. This is a proposed engineering gate, not a guarantee or a statistically sufficient model-performance sample. Delay annual plans until retention and support obligations are understood.

### P6 — Expansion after evidence

Fantasy tools, favorites/alerts, MLB/NHL/soccer/college sports and native apps are later candidates. Add one sport only after demand, data rights, entity mapping, sport-specific models and grading rules pass the same gates. Do not show a sport as supported just because a provider advertises it.

## 7. Budget and account checklist

USD 0 spent on services by this change. No Replit, proxy, advertising, domain, AI or data subscription purchase. The HTML has no external assets or API dependencies.

For the first pilot, a proposed allocation (not vendor quotations) is: optional domain up to USD 15, worker/testing allowance up to USD 10, AI testing up to USD 5, USD 70 reserve. Use free hosting/database only within verified limits. Defer the StatsHub subscription. A data subscription is not included in those allowances and needs a deliberate budget tradeoff. Do not auto-upgrade services or set uncapped provider fallback.

Required before activation: owner-controlled hosting account, Supabase project and policies, backend secret storage, provider credentials/permissions, alert destination, recovery/backup owner, later payment-processor eligibility and test-mode products. Account creation, identity verification, legal acceptance and purchases require owner action or explicit authorization; never ask for keys to be pasted into public code or chat.

## 8. Handoff and verification standard

Run:

```sh
python -m pip install playwright
python -m playwright install chromium
python tests/verify_platform_preview.py
# Or use an installed browser:
python tests/verify_platform_preview.py --browser /usr/bin/chromium
```

Generated `test-artifacts/` are local evidence, not production proof. Also test actual clickable cards/nav, back/forward, keyboard use, persistent sport selection, network failure and Safari before release.

Report each delivery in four distinct categories: code committed; local/CI tests; deployment status; live behavior verified. Never say fixed because a PR is merged or a workflow is green. The owner must be able to open the actual deployed URL and see the same release. If access is blocked, say what remains unverified instead of claiming success.

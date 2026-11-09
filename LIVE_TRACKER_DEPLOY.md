# Dedicated NBA live-stat service: deployment checklist

The Sports-Bot GitHub Pages site cannot run a continuous Python process. The
repository now contains an independently polled, read-only NBA live-stat
service. Deploy it on an **always-on** Python container host and then enable
the URL in the dashboard config. An autosleep/free web app is not a replacement
for guaranteed background polling.

## Runtime

- Container definition: `Dockerfile.live-tracker`
- Start command without Docker: `python -m iphone_bot.live_tracker_service`
- Bind port: environment variable `PORT` (default 8080).
- `LIVE_POLL_SECONDS=35` polls ESPN scoreboard and exact-match player boxes.
- `LIVE_CORS_ORIGIN=https://damiensandoval77-lang.github.io` restricts CORS.
- Public endpoints: `/healthz` and `/live_player_tracking.json`.
- Needs public HTTPS and an always-running instance. No sportsbook keys or
  wagering APIs are used.

## Activation

1. Deploy the container to a provider supporting 24/7 service instances.
   Confirm the deployment remains running without a browser tab open.
2. Visit `https://YOUR-SERVICE-HOST/healthz`. Expect `HEALTHY` with
   `last_success` and `coverage` after initial ESPN data acquisition. A
   match day can be healthy while no games have tipped off.
3. Confirm `/live_player_tracking.json` has the expected source identity,
   an observed `captured_at`, and `coverage.missing_fresh_matchups`.
4. Set `docs/live_tracker_config.json` to
   `{"status":"HOSTED_LIVE_SERVICE_ENABLED","url":"https://YOUR-SERVICE-HOST/live_player_tracking.json"}`.
   The website will then try this service first and automatically fall back
   to direct ESPN and the existing GitHub snapshot if it fails.

## Guarantees and limits

- Poll cadence is a **target**, not evidence that the upstream ESPN response is
  current. UI uses each game's `observed_at`, not just the file modification
  time. Server errors are visible and missing games are flagged.
- Matches require exact opponent identity and player team/name. Unknown
  players/DNPs are not zero; no post-tip predictions are invented.
- Stale observations are retained only for the same ESPN event/date for at
  most 30 minutes, and are explicitly marked stale.
- GitHub Actions remains a five-minute **backup**, not an always-on process.
- The service is **not hosted** by committing these files. A persistent external
  host and a confirmed HTTPS deployment are required to enable the new endpoint.

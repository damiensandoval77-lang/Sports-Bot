# iPhone sportsbook odds feed

This is an optional standalone feed for the GitHub Pages dashboard. It uses **The Odds API** v4, not the unofficial PrizePicks endpoint.

## Setup (iPhone)
1. Create an account and API key at https://the-odds-api.com/ .
2. Open this repository → Settings → Secrets and variables → Actions → New repository secret.
3. Name: `ODDS_API_KEY`; value: your personal key. Never paste the key into code or chat.
4. Open Actions → Update NBA sportsbook props → Run workflow.
5. Check the workflow log and reload the GitHub Pages dashboard.

Runs automatically once daily at 16:23 UTC (GitHub schedule timing can drift). Each run fetches the upcoming events list and **at most two NBA games** with four player-prop markets. API credits vary with markets actually returned and region; monitor usage in your provider dashboard. GitHub Actions writes results to `docs/data.json` so the public dashboard can read them.

**Current limitations:** Displays sportsbook prices, not PrizePicks lines. No trained AI projection is connected, no validated probability or EV calculation, no injury feed, no notifications, and no automated bets. Data is publicly visible on GitHub Pages. The free API plan's player-prop availability is not guaranteed; if the provider rejects a call, the workflow fails and leaves the previous dashboard data untouched. Avoid treating stale data as live.

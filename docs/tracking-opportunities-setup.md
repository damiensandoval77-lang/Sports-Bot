# Passing tracking & rebound chance challenger

Two new research shadows are available for NBA props. Neither alters the
production Combined AI or previously frozen projections.

## Input meaning

- **AST:** potential assists / tracked passing chances, separate from actual assists.
- **REB:** tracked rebound chances, separate from actual rebounds.
- Both predict expected opportunities from historical per-minute chance rates,
  convert to expected made assists/rebounds using historical conversion, and
  shrink a capped research adjustment toward frozen Combined AI.
- Rates have a minimum of 8 dated previous games and 160 tracked minutes.
  Unknown, overlapping, duplicate, future, stale, or invalid source data
  must be rejected. Unstable minutes also suppress the challenger.
- Results are graded only against the identical originally saved sportsbook
  line for the exact same player, event, market, and original pretip capture.

## Data contract (private source only)

The research script loads a local file at
`data/nba/private/tracking_opportunities.json`. This directory is gitignored.
This is the normalized schema for independently **licensed** game-level rows,
NOT proof a provider is connected:

```json
{
  "status": "AUTHORIZED_TRACKING_RESEARCH",
  "licensed_use_verified": true,
  "season": "2026-27",
  "source": "AUTHORIZED_PROVIDER",
  "generated_at": "2026-11-06T22:45:00Z",
  "authorization": {
    "allowed_use": "NBA_PROP_RESEARCH",
    "reviewer_confirmation": "MANUALLY_VERIFIED",
    "permission_reference": "YOUR_VERIFIED_PERMISSION_REFERENCE"
  },
  "observations": [
    {
      "player_id": "EXACT_NBA_ID",
      "team": "BOS",
      "game_id": "0022600001",
      "game_date": "2026-10-25",
      "observed_at": "2026-10-26T09:00:00Z",
      "minutes": 32,
      "potential_assists": 11,
      "assists": 6,
      "rebound_chances": 14,
      "rebounds": 7
    }
  ]
}
```

The placeholder player ID, game ID, dates and statistics above are *example
only*. Real values are not yet connected. Required rights status must reflect
actual externally verified licensing; a JSON flag cannot itself grant rights.

## Source and permission

Reference field definitions: https://www.nba.com/stats/help/glossary .
The NBA's published Statistics Terms (https://www.nba.com/termsofuse)
**explicitly prohibit use of their NBA Statistics in connection with gambling**
and require prior authorization for many other uses. Do **not** fetch NBA.com
tracking statistics into a betting-oriented model merely because their web
endpoint responds with HTTP 200. The public `nba_api` package and open-source
code do not grant the underlying statistical data rights. Obtain an authorized
tracking-stat provider/export that permits this usage.

## Current validation and results

The projection research pipeline and its test suite freeze alternative AST and
REB forecasts with unchanged Combined AI baseline. See:
- `iphone_bot/tracking_opportunities_v1.py`
- `iphone_bot/projection_upgrade_research.py`
- `docs/tracking_opportunities_validation_status.json` for GitHub Actions
  compile/test results.
- `docs/projection_upgrade_status.json` key
  `tracking_opportunity_shadow` for actual settled future paired samples.

No real licensed tracking feed has been connected yet. **No improvement in
assist or rebound hit rate is claimed until future-grade records exist.**

## Import an authorized CSV export

A source with confirmed rights can export one row per player/game using this
exact header:

```text
player_id,team,game_id,game_date,observed_at,minutes,potential_assists,assists,rebound_chances,rebounds
```

Use an independently verified permission manifest, containing
`season`, `source`, `generated_at`, `allowed_use`,
`reviewer_confirmation`, and `permission_reference`. Never set the rights
fields to verified without an actual permitted-use basis.

```bash
python -m iphone_bot.import_tracking_export \
  --csv /secure/tracking-player-games.csv \
  --authorization /secure/provider-permissions.json
```

The import validates rows and writes only to the gitignored private research
feed. CI checks the importer against synthetic data, but an ordinary GitHub
Actions runner **does not** have access to locally imported private files.
For unattended source updates, a permitted server-side feed and secure
deployment are still required.

## Actual provider connection progress — November 8, 2026

I verified the published schema of **SportQuanta** at
https://docs.sportquanta.com/api-reference/endpoints/basketball/nba/list-nba-player-tracking/ .
It explicitly includes `passing.potential_assists` and
`rebounding.rebound_chances`. Its public docs also state that the player
tracking API is behind the paid **stats** entitlement and requires an
`Authorization: Bearer` token. The documented response is a
**season-level player summary**, not a set of verified independent
player/game observations, so it cannot be fed directly to the prospective
game-level model or counted as >=8 historical games. A plan or token alone
therefore does not yet complete per-game tracking integration.

New repository-only readiness diagnostics:
- `iphone_bot/probe_tracking_provider.py` makes **one** bounded request to
  the documented `/v1/nba/player-tracking?season=2026&limit=500` endpoint,
  manually, with token from the GitHub Actions secret
  `SPORTQUANTA_API_KEY` only. It publishes no raw player statistics.
- `.github/workflows/nba-tracking-provider-access.yml` runs schema-only
  tests on push without a paid HTTP call. On manual dispatch, it attempts the
  provider check using that secret, never publishing it.
- `docs/tracking_provider_access_status.json` currently reports
  `NOT_CONFIGURED_NEEDS_PROVIDER_TOKEN`.
- `docs/tracking_coverage_status.json` refreshes automatically when the
  research board or provider status changes and explains whether actual
  player-game observations have been graded. An empty current board does not
  mean zero accuracy.

**If a SportQuanta subscription and properly authorized source are available**,
add `SPORTQUANTA_API_KEY` to GitHub repo Settings → Secrets and variables →
Actions → New repository secret. Then manually run "Inspect NBA potential-assist
and rebound-chance provider safely" from the Actions tab. This only confirms
entitlement and response structure; it does not yet prove the subscription
includes the historical per-game samples required by this model.

As a betting-oriented UI, `Outlier.bet` documents potential assists and
rebound chances (https://help.outlier.bet/en/articles/9005352-potential-assists-rebound-chances-nba-advanced-data),
but no supported per-game export/API licensing contract has been verified.
`DunkAPI` allows product/model use under its published terms and offers
play-by-play/box scores, but does **not** document the exact optical tracking
metrics required here; its play-by-play should never be relabeled as measured
potential assists or rebound chances.

**Missing prerequisite for live data use:** One permitted per-game player
tracking export/API, covering each player, actual `game_id` + `game_date`,
minutes, potential assists, and rebound chances. No existing connected
account or API key for such data was available in this session.

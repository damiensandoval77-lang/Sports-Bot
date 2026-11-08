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

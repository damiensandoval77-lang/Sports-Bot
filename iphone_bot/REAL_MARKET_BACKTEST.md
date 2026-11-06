# Real sportsbook NBA prop backtesting

This is **not** the synthetic-line backtest. It uses genuine two-sided
sportsbook quotes captured before tipoff and real player box-score outcomes.

## Automatic collection

`.github/workflows/nba-props.yml` now saves complete pregame Over/Under pairs
from the existing The Odds API feed to:

`data/nba/odds/observed_props.csv`

The archive contains player name, Eastern game date, market (PTS/REB/AST/PRA),
sportsbook, half-point line, both American odds, UTC capture timestamp,
UTC event start, and source. It **never backfills** odds that were not seen.

The scanner currently collects only the next two scheduled games per run
and runs once daily, so coverage will be sparse. Additional API calls can
consume quota. The current feed is **sportsbook prices, not PrizePicks**.

## Historical import

Licensed historical sportsbook CSVs may be normalized to this schema:

`game_date,player_name,market,bookmaker,line,over_odds,under_odds,captured_at,event_start,game,source`

Example field formats (ILLUSTRATIVE ONLY, NOT A REAL QUOTE):
- `game_date` as `YYYY-MM-DD` in America/New_York;
- `market` in `PTS, REB, AST, PRA`;
- half-point numeric `line`;
- American prices `-110`, `105` etc;
- `captured_at` and `event_start` as ISO timestamps with offsets.

Do not invent `captured_at`, reconstruct a price from the final score,
or label post-tipoff odds as pregame odds. Verify player identity, team,
sportsbook provenance, and timezone before importing.

## Running the real-market test

The workflow `nba-backtest-real-market.yml` rebuilds historical features,
joins quotes to final box scores, trains on older seasons, calibrates on
later data, and evaluates price-matched results on a held-out date window.

Until real quotes overlap with completed games in the historical box-score
archive, this workflow will **intentionally fail** with an explanation.
The currently downloaded season archive only goes through April 2026;
new quotes from November 2026 do not yet have matching final box scores.
Daily score ingestion or licensed historical market data is needed.

Reports are exploratory and not proof of profitability: multiple markets
for the same player/game are correlated; historical lines may be biased by
survivorship, selection and unavailable-at-bet-time issues; the feature
generation pipeline still needs an independent leakage review.

The Odds API historical prop snapshots are paid-tier. A provider with a
limited free allowance is DunkAPI; connection and a separate key are
required and historical coverage is incomplete.

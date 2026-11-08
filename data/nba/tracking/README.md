# NBA tracking opportunities — authorized historical feed

This directory accepts **actual player-game tracking data** for research. These
statistics are not recoverable exactly from box scores or play-by-play.

## Where to obtain

NBA Stats player **Tracking > Passing** and **Tracking > Rebounding**:
- https://www.nba.com/stats/players/passing
- https://www.nba.com/stats/players/rebounding

The official `LeagueDashPtStats` endpoint supports `PtMeasureType=Passing`
and `PtMeasureType=Rebounding`, plus `DateFrom` and `DateTo` filters.
Access may be restricted, blocked in GitHub Actions, or subject to provider
licensing/terms. Use authorized exports or another provider with rights to the
data. Do **not** invent statistics if requests are refused.

## Input contract

Provide an authorized CSV as `data/nba/tracking/authorized_tracking_games.csv`
with one player/team/game-date row (team abbreviations as in the model). Required:

`player_id,game_date,team,source,source_reference`

Optional actual tracking metric columns (at least one required):

`potential_assists,passes_made,touches,assist_points_created,rebound_chances,rebound_chance_pct,contested_rebounds,uncontested_rebounds,offensive_rebound_chances,defensive_rebound_chances`

Example format **ONLY** (the example below is invented to show the shape and
MUST NEVER be used as real training or prediction evidence):

```csv
player_id,game_date,team,source,source_reference,potential_assists,rebound_chances
EXAMPLE_ID,2026-11-01,BOS,EXAMPLE_NOT_REAL,example-only,12,10
```

Use real NBA player IDs, actual observations and an accessible provenance
reference in production. If using a data vendor, record the specific
dataset/date. Do not commit restricted vendor data to the public repository.

## Model integration

`iphone_bot/tracking_opportunity_features.py` reads this file only if present.
It rejects identity conflicts, checks provenance, and computes L5/L10/season
rolling means from dates **strictly earlier than the upcoming matchup**.
Research metrics appear in expanded player cards after the next AI-board
refresh. There is no silent replacement for missing player tracking.

**Current status:** research-only, no production AI weight changes and no
verified prediction improvement. Historical accuracy should be compared on
identical future matches before using these features to adjust prop picks.
